# NB03 — Falhas e observabilidade (`03_falhas_e_observabilidade.ipynb`)

**Pergunta:** o que acontece quando algo dá errado, e como eu vejo?
**Partida → chegada:** `v2` → `v3` (`erros_estruturados`, `retry`, `fallback`,
`limites`, `persistencia`, `idempotencia`).

**Ideia central:** robustez é continuar se comportando bem quando algo falha, e só dá
para tratar o que se consegue ver. Toda seção a partir de N3.2 **injeta** uma falha e
**mostra no Phoenix** como o sistema reage. Todas as falhas deste notebook são induzidas,
e as células dizem isso.

**Ao final, o participante sabe:**
- ler um trace e reconstruir a trajetória de um atendimento;
- transformar erro de ferramenta em informação para o agente;
- tratar falhas do modelo com retry e fallback;
- limitar a execução;
- sobreviver à queda do processo;
- por que idempotência é responsabilidade do sistema, não do framework.

**Composições por seção:**

| Seção | Falha | Correção |
|---|---|---|
| N3.0 | — | `v2` |
| N3.1 | `v2.sem("sequencia")` (gravação de N2.5) | `v2` |
| N3.2 | `v2` | `+ erros_estruturados` |
| N3.3 | correção de N3.2 | `+ retry + fallback` |
| N3.4 | correção de N3.3 | `+ limites` |
| N3.5 | correção de N3.4 | `+ persistencia` |
| N3.6 | correção de N3.5 | `+ idempotencia` = `v3` |

**Tipos de falha injetáveis** (`falhas.injetar(tipo, **opcoes)`, sempre em `with`):

| Tipo | Opções | Efeito |
|---|---|---|
| `ferramenta_fora` | `alvo` | a ferramenta lança `ConnectionError` |
| `modelo_429` | `vezes` | as próximas *n* chamadas ao modelo primário falham com 429 |
| `modelo_timeout` | `vezes` | idem, com timeout |
| `modelo_fora` | — | o modelo primário falha sempre (força fallback) |
| `resultado_ambiguo` | `alvo` | a ferramenta devolve sempre "resultado incompleto, tente de novo" |
| `timeout_apos_efeito` | `alvo` | a ferramenta executa o efeito e depois lança `TimeoutError` |

A injeção fica **acima** da fonte de respostas na pilha do modelo, então funciona em
`replay`; o retry fica acima da injeção e a enxerga.

## Seções

### N3.0 — Ligando a observabilidade
- `preparar_ambiente()` já instrumentou o ADK (OpenInference → Phoenix local).
- Anatomia do trace de `C01` em `v2`: atendimento → agentes da sequência → chamadas ao
  modelo → ferramentas, com tokens, latência e a fonte da resposta (cache, gravação,
  roteiro, live).
- **Sem Phoenix:** a mesma anatomia em tabela, a partir de `a.eventos`.
- **Verificação:** `a.trace_url` existe (ou aviso, sem Phoenix).

### N3.1 — O trace mostra o desvio de fluxo
- **Cenário:** `C03`.
- **Falha (a gravação de N2.5):** a resposta final parece correta; só o trace mostra que o
  reembolso foi registrado sem `buscar_pedido` antes.
- **Conceito:** a trajetória é o objeto a observar. Esta é a falha "desvio de fluxo" do
  PDC.
- **Verificação:** `ferramenta_antes(...)` é falso na falha e verdadeiro em `v2`.
- **Ponte:** a mesma função vira teste em N4.5.

### N3.2 — Ferramenta fora do ar
- **Cenário:** `C03`, com `falhas.injetar("ferramenta_fora", alvo="buscar_pedido")`.
- **Falha:** em `v2`, a exceção encerra o atendimento com `status == "erro"`.
- **Conceito:** `erros_estruturados`: um `on_tool_error_callback` converte a exceção em
  resultado (`{"erro": "indisponivel", "tentar_novamente": false}`); o agente lê e escala.
  Degradar para um humano é uma resposta robusta, não um fracasso.
- **Correção:** no Phoenix, o span da ferramenta com erro e o atendimento concluído.
- **Verificação:** `status == "escalado"`; nenhum reembolso.

### N3.3 — Modelo indisponível
- **Cenário:** `C02`.
- **Falhas:** `modelo_429` (`vezes=2`), depois `modelo_fora`.
- **Conceito:** `retry` com backoff exponencial para falhas transitórias (429, timeout);
  `fallback` para o modelo secundário quando o primário persiste em falhar. Os dois são
  camadas do `BaseLlm` composto do RangoJá (`mostrar(resiliencia.retry)`). Mencionar as
  alternativas de produção (opções de retry do `google-genai`, roteadores como LiteLLM).
- **Correção:** no trace, as tentativas e a troca de modelo.
- **Verificação:** com 429 ×2, concluído com 3 tentativas; com primário fora, concluído
  pelo modelo de fallback (registrado em `a.eventos`).

### N3.4 — O agente que não para
- **Cenário:** `C01`, com `falhas.injetar("resultado_ambiguo", alvo="buscar_pedido")`.
- **Falha:** em `v2`, o agente chama `buscar_pedido` repetidamente (teto padrão do ADK:
  500 chamadas ao modelo). A célula interrompe após 15 chamadas e mostra a contagem.
- **Conceito:** `limites`: `RunConfig(max_llm_calls=...)` e um limite de chamadas por
  ferramenta em `before_tool_callback`; ao atingir, escalar.
- **Verificação:** `contar_chamadas(a, "buscar_pedido") <= 3`; `status == "escalado"`.

### N3.5 — O processo caiu com um reembolso pendente
- **Cenário:** `C09`; `preparar_secao` cria a pendência (`aguardando_aprovacao`).
- **Falha:** `reiniciar_runner()` com sessão em memória → a pendência some; aprovar não
  tem o que retomar.
- **Conceito:** `persistencia`: `SqliteSessionService` + `App` com
  `ResumabilityConfig(is_resumable=True)`. Após reiniciar, `aprovar(a)` retoma a execução
  pelo `invocation_id`.
- **Verificação:** depois de reiniciar e aprovar, exatamente um reembolso registrado.
- **Gancho para N3.6:** a documentação do próprio ADK diz que a retomada é "pelo menos uma
  vez" e que a ferramenta retomada precisa ser idempotente.

### N3.6 — Reembolso em dobro
- **Cenário:** `C03`.
- **Falha (a):** `timeout_apos_efeito` em `registrar_reembolso`: o reembolso acontece, a
  confirmação se perde, o agente recebe o erro e chama de novo → dois reembolsos.
- **Falha (b):** `C09` aprovado, com `timeout_apos_efeito`; a retomada refaz a chamada →
  dois reembolsos.
- **Conceito:** frameworks garantem "pelo menos uma vez"; "exatamente uma vez" no efeito
  colateral exige **idempotência**: chave `(pedido_id, motivo)` verificada na ferramenta
  antes de agir; a segunda chamada devolve o resultado da primeira.
- **Correção:** `v3` nos dois cenários.
- **Verificação:** um único reembolso no registro em (a) e em (b).

### N3.7 — Recapitulação e métricas
Tabela: falha injetada → reação do sistema → onde se vê no Phoenix. Mostrar métricas
agregadas do Phoenix ao longo das execuções do notebook (taxa de erro de ferramenta, taxa
de escalonamento, latência p50/p95) como ponte para monitoramento contínuo. Ponte para o
NB04: "o sistema reage bem *nestes* casos; como garantir que continua reagindo depois da
próxima mudança?".
