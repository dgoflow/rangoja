# Extras (`extras/`)

> Especificação original do notebook, mantida como registro. O notebook em si e o
> [`notebooks/README.md`](../README.md) descrevem o que existe hoje; os desvios estão em
> [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

Notebooks opcionais, independentes entre si e dos principais. Seguem o mesmo padrão de
seção, usam `preparar_secao` e o catálogo de casos.

| Notebook | Tema | Conteúdo mínimo | Verificação |
|---|---|---|---|
| `x1_memoria_pesquisavel.ipynb` | Memória de sessões passadas | `MemoryService` do ADK (em memória) e a ferramenta de busca na memória; o agente recupera atendimentos anteriores do cliente; o que pode e o que não pode virar memória (retoma N2.4) | o agente cita o atendimento anterior correto e nenhum direito alegado |
| `x2_conversas_longas.ipynb` | Contexto em conversas longas | Conversa de 20 turnos gerada a partir de `C11`; resumo contínuo e janela deslizante; tokens antes/depois; risco de o resumo perder `pedido_id` ou compensações já dadas (por que o estado estruturado de N1.5 é mais confiável que o resumo) | o estado estruturado sobrevive à compressão |
| `x3_dados_sinteticos.ipynb` | Ampliar o golden dataset | Gerar reclamações por persona e cenário; filtrar duplicatas; revisão humana; gerar variantes metamórficas e checar se preservam o sentido | variantes aceitas mantêm a categoria esperada |
| `x5_execucao_duravel.md` | Quando o fluxo fica longo | Texto, sem código: o que um motor de workflow durável (ex.: Temporal) acrescenta à retomada de N3.5 (timers duráveis, sinais, histórico); quando vale a pena | — |

Removido da proposta original: `x4_langfuse` (mesmos traces em outro backend). O backend de observabilidade do material é só o Phoenix.

Fora do escopo: embeddings e busca vetorial, BAML, otimização de prompts com DSPy.
