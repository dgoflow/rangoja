# NB02 — Controle de comportamento (`02_controle.ipynb`)

> Especificação original do notebook, mantida como registro. O notebook em si e o
> [`notebooks/README.md`](../README.md) descrevem o que existe hoje; os desvios estão em
> [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

**Pergunta:** como impedir que o agente faça o que não deve?
**Partida → chegada:** `v1` → `v2`.

**Ideia central:** *o modelo propõe, o código autoriza.*

**Ao final, o participante sabe:**
- exigir aprovação humana para ação irreversível, por regra e não por prompt;
- proteger a entrada e a saída;
- separar memória útil de memória perigosa;
- quando orquestrar em etapas fixas;
- restringir ferramentas e soluções conforme a categoria;
- validar o que passa entre etapas.

**Composições por seção** (cada correção acrescenta um componente à anterior):

| Seção | Falha | Correção |
|---|---|---|
| N2.1 | `v1` | `montar(v1, com=["aprovacao"])` |
| N2.2 | `montar(v1, com=["aprovacao"])` | `+ guardrail_entrada` |
| N2.3 | roteiro sobre a correção de N2.2 | `+ guardrail_saida` |
| N2.4 | correção de N2.3 (com `memoria_livre`) | `memoria_livre → memoria_segura` |
| N2.5 | `v2.sem("sequencia")` (implica sem `categorias` e `contrato`) | `+ sequencia` |
| N2.6 | `v2.sem("categorias")` | `+ categorias` |
| N2.7 | `v2.sem("contrato")` | `+ contrato` = `v2` |

## Seções

### N2.1 — Limite e aprovação humana
- **Cenário:** `C09` (R$ 120).
- **Falha (gravação ou roteiro, ver `casos.md`):** reembolso automático de R$ 120.
- **Conceito:** `registrar_reembolso` vira `FunctionTool(..., require_confirmation=lambda
  valor, **_: valor > 50)`. A execução pausa (`a.status == "aguardando_aprovacao"`); o
  supervisor responde depois. Dentro do mesmo processo, a pendência vive na sessão em
  memória (a durabilidade é o tema de N3.5).
- **Correção:** três células: `aprovar(a)` → reembolso feito; `recusar(a, "valor alto")`
  → agente oferece alternativa ou escala; `relogio.avancar(horas=25)` +
  `expirar_pendencias()` → escala por prazo vencido.
- **Verificação:** antes da resposta do supervisor, `contar_chamadas` efetivas de
  `registrar_reembolso` = 0; após aprovar, = 1; após recusar ou expirar, = 0 e
  `status == "escalado"` no caso do prazo.

### N2.2 — Guardrail de entrada
- **Cenários:** `C05` (injeção) e `C10` (fora do escopo).
- **Falha:** `C05` chega à ferramenta pedindo R$ 300 (a aprovação de N2.1 segura o
  dinheiro, mas o pedido nunca deveria ter chegado lá); `C10` gasta chamadas com assunto
  fora do escopo.
- **Conceito:** `before_model_callback` com regras: padrões de injeção, assunto fora do
  escopo, PII do próprio cliente (mascarar cartão). Defesa em camadas: se o guardrail
  falhar, o limite de N2.1 continua valendo.
- **Verificação:** em `C05`, nenhuma chamada a `registrar_reembolso`; em `C10`, resposta
  de recusa sem chamadas de ferramenta.
- **Experimente:** escrever um ataque novo e ver qual camada o pega.

### N2.3 — Guardrail de saída
- **Cenário:** `C12`.
- **Falha (roteiro):** a resposta do modelo inclui o telefone do entregador. Explicar por
  que é roteiro: o `contexto_enxuto` de N1.6 já impede que o modelo veja o telefone; o
  roteiro simula uma regressão dessa camada.
- **Conceito:** `after_model_callback` inspeciona a resposta antes de ela sair, contra os
  dados reais de `entregadores.json` (regra do domínio), e não por lista de palavras.
- **Verificação:** a resposta final não contém nenhum valor de `entregadores.json`.

### N2.4 — Memória útil × memória perigosa
- **Cenários:** `C07` (recorrência) e `C08` (envenenamento, dois atendimentos).
- **Falha (gravação ou roteiro):** `C07` recebe o 4º reembolso; em `C08` o agente grava
  "cliente tem direito a reembolso integral" com `anotar_observacao` e, no atendimento 2,
  oferece reembolso integral.
- **Conceito:** `memoria_segura`: (a) o histórico de reembolsos (`user:reembolsos_30d`) é
  gravado só por `registrar_reembolso` e lido num `before_tool_callback` que aplica a
  regra de recorrência; (b) `anotar_observacao` é substituída por
  `registrar_preferencia(campo, valor)` com campos permitidos (entrega, contato). Fatos
  vêm do sistema; alegações do cliente não viram memória.
- **Verificação:** `C07` com `status == "escalado"` e nenhum reembolso; `C08` sem
  nenhuma chave de memória criada no atendimento 1 e sem reembolso no atendimento 2.

### N2.5 — Determinístico × autônomo
- **Cenário:** `C03`.
- **Falha (gravação ou roteiro):** o agente único registra o reembolso sem consultar o
  pedido.
- **Conceito:** o que tem ordem fixa vira `SequentialAgent` (triagem → resolução →
  resposta); o modelo decide **dentro** de cada etapa, não a ordem delas. Discutir quando
  vale deixar o modelo orquestrar (subagentes com `transfer_to_agent`) e o custo disso.
  Exibir a árvore de agentes e o estado que cada etapa grava (`output_key`).
- **Verificação:** `ferramenta_antes(a, "buscar_pedido", "registrar_reembolso")`.
- **Nota:** o trace desta falha é reaproveitado em N3.1.

### N2.6 — A categoria define o que é permitido
- **Cenário:** `C04` (golpe).
- **Falha (gravação ou roteiro):** o agente oferece reembolso para quem relatou golpe.
- **Conceito:** a triagem devolve a categoria e `sinais_de_risco`. Duas camadas:
  `before_model_callback` remove do pedido ao modelo as ferramentas não permitidas para a
  categoria (*progressive disclosure*: o modelo nem as vê); `before_tool_callback`
  bloqueia mesmo assim. Golpe só permite `encaminhar_seguranca`. Mostrar a tabela de
  `controle/categorias.py`.
- **Verificação:** `chamou(a, "encaminhar_seguranca")`, nenhum `registrar_reembolso` nem
  `oferecer_cupom`; `status == "encaminhado_seguranca"`.

### N2.7 — Contrato entre etapas
- **Cenário:** `C06` (sem número do pedido).
- **Falha (gravação ou roteiro):** a triagem devolve `pedido_id: null` com schema válido; a
  resolução decide mesmo assim.
- **Conceito:** o schema garante a **forma**; o contrato garante o **conteúdo** de que a
  próxima etapa precisa (`controle/contrato.py`, verificado entre as etapas). Sem pedido,
  o fluxo volta ao cliente. Esta é a falha "quebra silenciosa de contrato" do PDC.
- **Verificação:** `a.decisao is None` e `a.status == "aguardando_cliente"`; depois,
  `continuar(a, "É o 6610")` produz decisão.

### N2.8 — Recapitulação
Tabela: camada de controle × caso que ela barrou × onde vive (callback, ferramenta,
orquestração). Ponte para o NB03: "agora o agente se comporta; e quando o mundo à volta
falha?".
