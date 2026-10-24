# NB01 — Do prompt ao agente (`01_do_prompt_ao_agente.ipynb`)

> Especificação original do notebook, mantida como registro. O notebook em si e o
> [`notebooks/README.md`](../README.md) descrevem o que existe hoje; os desvios estão em
> [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

**Pergunta:** o que separa um prompt de um agente?
**Partida → chegada:** `v0` (agente sem ferramentas, política colada) → `v1`
(`ferramentas`, `schema`, `estado`, `contexto_enxuto`, `memoria_livre`).

**Ao final, o participante sabe:**
- por que um modelo sem ferramentas inventa fatos;
- o que um agente faz por baixo do framework (o loop);
- por que a decisão precisa ser estruturada e a resposta ao cliente pode ser prosa;
- onde guardar o que a conversa já estabeleceu e o que deixar fora do contexto;
- como o agente pode lembrar do cliente entre atendimentos.

**Composições por seção** (correções cumulativas):

| Seção | Falha | Correção |
|---|---|---|
| N1.1 | `v0` | — |
| N1.2 | `v0` | `montar(v0, com=["ferramentas"])` |
| N1.3 | — | (a de N1.2) |
| N1.4 | `v0` | `+ schema` |
| N1.5 | `v1.sem("estado", "contexto_enxuto", "memoria_livre")` | `+ estado` |
| N1.6 | `v1.sem("contexto_enxuto", "memoria_livre")` | `+ contexto_enxuto` |
| N1.7 | `v1.sem("memoria_livre")` | `+ memoria_livre` = `v1` |

## Seções

### N1.1 — O prompt que funciona na demo
- **Cenário:** `C01`. A `v0` recebe a política inteira na instrução.
- **Falha (gravação):** resposta plausível; status do pedido e valor do reembolso
  inventados. Uma célula põe lado a lado o que a resposta afirma e o que está em
  `pedidos.json`.
- **Conceito:** o modelo só sabe o que está no contexto; texto plausível não é fato.
- **Verificação (contra a gravação):** o valor afirmado difere do valor real.
- Fecha com a pergunta em aberto: como dar fatos ao modelo?

### N1.2 — Ferramentas trazem fatos
- **Cenário:** `C01`.
- **Conceito:** `LlmAgent` com `buscar_pedido` e `consultar_politica`. `mostrar` as duas
  funções: a docstring e os tipos são o que o modelo lê para decidir usá-las.
- **Correção:** a trajetória mostra as chamadas; a resposta cita o valor real (R$ 8).
- **Verificação:** `chamou(a, "buscar_pedido")`; o valor citado é 8.
- **Experimente:** apagar a docstring de `buscar_pedido` (cópia local) e ver o agente
  deixar de usá-la.

### N1.3 — O loop por baixo
- **Conceito:** percorrer `a.eventos` de N1.2 e imprimir uma linha por passo: o modelo pede
  uma ferramenta → a ferramenta responde → o modelo decide o próximo passo ou responde.
  Diagrama curto em markdown. Não reimplementar o loop; só torná-lo visível.
- **Verificação:** ≥ 3 passos; o último é a resposta final.

### N1.4 — Prosa × estrutura
- **Cenário:** `C02`.
- **Falha (gravação, v0):** decisão em prosa ("vou te dar um desconto na próxima"). Uma
  célula tenta extrair categoria e valor com regex e falha.
- **Conceito:** a **decisão** é um contrato com o código (`output_schema` = `Decisao`); a
  **resposta** ao cliente continua em prosa, escrita a partir da decisão. Nota: com a API
  do AI Studio, o ADK entrega a saída estruturada por uma ferramenta interna
  (`set_model_response`), que aparece no trace e é ignorada pelas funções de trajetória.
- **Correção:** `a.decisao` tipada e `a.resposta` em texto.
- **Verificação:** `a.decisao.categoria == "atraso"` e
  `a.decisao.solucao in solucoes_permitidas("atraso")`.

### N1.5 — Estado da conversa
- **Cenário:** `C11` (3 turnos).
- **Falha (gravação, cada turno em sessão nova):** no turno 3 o agente pede o número do
  pedido de novo e compensa a sobremesa como um atendimento separado.
- **Conceito:** o que a conversa estabeleceu (pedido, categoria, compensações) fica no
  **estado da sessão** (`output_key`, `session.state`), e as ferramentas leem e gravam
  ali. Exibir `a.turnos[i]` e o estado a cada turno.
- **Verificação:** `contar_chamadas(a, "buscar_pedido") == 1`; compensação consolidada de
  R$ 20.

### N1.6 — O que entra no contexto
- **Cenário:** `C01`.
- **Falha (determinística):** sem `contexto_enxuto`, `buscar_pedido` devolve o pedido
  inteiro com o entregador embutido. Mostrar o tamanho da requisição ao modelo e os
  campos de PII que entraram nela.
- **Conceito:** engenharia de contexto: cada ferramenta devolve só o que a decisão precisa;
  a política entra por consulta (`consultar_politica(tema)`), não colada.
- **Correção:** comparar tokens da requisição antes/depois.
- **Verificação:** nenhum campo de `entregadores.json` na requisição enviada ao modelo.

### N1.7 — Lembrar do cliente
- **Cenário:** `C13` (dois atendimentos do mesmo cliente).
- **Falha (determinística):** sem memória, o atendimento 2 não sabe da preferência.
- **Conceito:** estado com prefixo `user:` persiste entre sessões do mesmo cliente;
  `anotar_observacao(texto)` grava observações livres em `user:observacoes`, lidas no
  início de cada atendimento. Avisar: memória livre é uma porta de entrada (retomado em
  N2.4).
- **Verificação:** a resposta do atendimento 2 menciona a portaria.

### N1.8 — Recapitulação
Tabela: problema → componente → módulo do pacote. Ponte para o NB02: "o agente agora age
e lembra; nada ainda o impede de agir mal".
