# Registro de decisões das specs

Decisões tomadas na revisão v0.1 → v0.2 das specs, sem consulta, com o critério
**"na dúvida, escolher a opção mais completa"**. Cada decisão referencia o problema
encontrado na revisão (A1…D4). Revisar e reverter o que não fizer sentido.

## Verificação no ADK 1.33.0

Feita no código-fonte do pacote `google-adk==1.33.0` (mesma versão do PDC1), instalado
num ambiente descartável em 2026-10-21.

| Recurso | Resultado | Onde no ADK |
|---|---|---|
| `output_schema` + `tools` no mesmo `LlmAgent` | **Suportado.** Com Gemini via API do AI Studio, o ADK usa um contorno: expõe uma ferramenta interna `set_model_response` para a saída final. Com Vertex AI (Gemini 2+) ou `LiteLlm`, o schema é nativo | `agents/llm_agent.py` (nota do campo `output_schema`), `utils/output_schema_utils.py`, `flows/llm_flows/_output_schema_processor.py` |
| Callbacks como lista | **Suportado** para `before/after_model`, `before/after_tool`, `on_model_error`, `on_tool_error`. Executados em ordem; o primeiro que devolve valor interrompe os seguintes | `agents/llm_agent.py` (aliases `*Callback`) |
| Plugins | Existem e rodam **antes** dos callbacks do agente; se um plugin devolve resposta, os callbacks do agente não rodam | `plugins/`, `flows/llm_flows/base_llm_flow.py` |
| Limite de chamadas | `RunConfig.max_llm_calls` (padrão 500) | `agents/run_config.py` |
| Prefixos de estado | `app:`, `user:`, `temp:` | `sessions/state.py` |
| Sessão em banco | `SqliteSessionService(db_path)` e `DatabaseSessionService` | `sessions/` |
| Confirmação humana de ferramenta | `FunctionTool(..., require_confirmation=bool \| callable)`; o callable recebe os argumentos (ex.: `valor > 50`). A pausa vira a chamada `adk_request_confirmation`; a resposta leva `ToolConfirmation(confirmed=...)` | `tools/function_tool.py`, `tools/tool_confirmation.py`, `flows/llm_flows/functions.py` |
| Retomada | `App(resumability_config=ResumabilityConfig(is_resumable=True))`; `Runner.run_async(invocation_id=...)`. O próprio ADK avisa: a retomada é "pelo menos uma vez", a ferramenta precisa ser idempotente, e estado temporário se perde | `apps/app.py`, `runners.py` |
| Avaliação | `AgentEvaluator.evaluate(agent_module=...)` procura `root_agent` num módulo `agent` (pacote com `agent.py`). Métricas: `tool_trajectory_avg_score` (casamento `EXACT`, `IN_ORDER`, `ANY_ORDER`), `response_match_score`, `final_response_match_v2`, `rubric_based_tool_use_quality_v1`, `hallucinations_v1`, `safety_v1`, métricas multi-turno | `evaluation/` |
| Modelo customizado | Subclasse de `BaseLlm` com `generate_content_async` | `models/base_llm.py` |

Não verificado (fazer na implementação): pacote `openinference-instrumentation-google-adk`
compatível com 1.33 (o PDC1 usa ≥ 0.1.4) e o comportamento dos spans quando a resposta
vem de um `BaseLlm` customizado.

## Decisões

### Desacoplamento
- **A1 — Versões montáveis.** Cada versão é uma montagem de componentes nomeados.
  `montar(base, com=[...], sem=[...])` cria variantes; `v2.sem("contrato")` é atalho.
  Dependências entre componentes são resolvidas automaticamente (desligar `sequencia`
  desliga `categorias` e `contrato`). Cada seção declara a composição exata da falha e
  da correção. As correções dentro de um notebook são **cumulativas**: a seção *k*
  acrescenta um componente à seção *k−1*.
- **A1 — Versões como pacotes de agente.** `rangoja/versoes/v1/agent.py` com `root_agent`,
  porque o `AgentEvaluator` exige essa forma.
- **A2 — Estado inicial por seção.** Registro em `rangoja/secoes.py`: para cada ID de
  seção, a versão, o caso, as sementes (memória, reembolsos anteriores, pendências) e
  as gravações. `preparar_secao(id)` constrói tudo; nenhuma seção depende de outra.
- **A3 — Isolamento.** `preparar_secao` cria armazenamentos novos (banco SQLite
  temporário por seção) para sessões, memória `user:`, registro de reembolsos, chaves
  de idempotência e pendências, e desliga falhas injetadas.
- **A4 — Injeção só em contexto.** `with falhas.injetar(...):`.

### Modelo, cache e gravações
- **B1 — `output_schema` + ferramentas no mesmo agente**, usando o suporte do ADK. As
  funções de trajetória ignoram ferramentas internas (`set_model_response`,
  `adk_request_confirmation`, `transfer_to_agent`).
- **B3 — Gemini direto (API do AI Studio), sem LiteLLM.** Retry e fallback são código do
  próprio RangoJá, visível no NB03 (`resiliencia/retry.py`). Alternativas de produção
  (opções de retry do `google-genai`, LiteLLM) entram como menção. Os modelos são
  configuração (`RANGOJA_MODELO`, `RANGOJA_MODELO_FALLBACK`, `RANGOJA_MODELO_JUIZ`); o
  juiz é de outra família de tamanho, diferente do agente. Os IDs exatos são fixados na
  implementação e gravados nos metadados de cada gravação.
- **B2 — Pilha do modelo.** Tudo fica **abaixo** dos callbacks (guardrails sempre rodam),
  dentro de um `BaseLlm` composto, de fora para dentro:
  `fallback → retry → injeção de falhas → fonte (cache | gravação | roteiro | Gemini)`.
  Assim, falhas injetadas acontecem também em `replay` e o retry as enxerga. Cache não
  é plugin (plugins pulariam os guardrails).
- **B4 — Três fontes de resposta do modelo:**
  - *cache* por hash da requisição, para células comuns;
  - *gravação nomeada* (`rangoja/gravacoes/<secao>/<nome>.json`): sequência de respostas
    reais de um atendimento, com modelo, data, versão e hash de cada requisição; em
    `replay` é servida em ordem e avisa se a requisição atual divergir (gravação
    desatualizada);
  - *roteiro*: respostas escritas à mão (falha induzida, mock do NB04).
  Antes de escrever os notebooks, uma **rodada exploratória** tenta obter cada falha
  "gravada" em `live` (até 10 tentativas). Se não aparecer, a seção passa a usar roteiro
  e a spec é atualizada. A tabela da rodada está em `casos.md`.
- **B5 — Asserções em células de falha** rodam só contra gravação ou roteiro; em `live`,
  viram aviso.

### Controle
- **B6 — Aprovação humana** = `require_confirmation` com callable (`valor > limite`) em
  `registrar_reembolso`. Helpers `aprovar()`, `recusar()`; prazo com relógio injetável
  (`rangoja.relogio`) e `expirar_pendencias()`, que recusa com motivo "prazo vencido"
  e leva o agente a escalar. `Atendimento.status` ganha `aguardando_aprovacao`.
- **B7 — Persistência só na v3.** Na v2 a pendência vive na sessão em memória (mesmo
  processo); a v3 usa `SqliteSessionService` + `App` retomável.
- **B8 — Memória.** O registro de reembolsos (sistema) é a fonte de verdade;
  `registrar_reembolso` atualiza o registro e `user:reembolsos_30d`. Para haver uma
  falha real de envenenamento, a v1 tem `anotar_observacao(texto)` (memória livre em
  `user:observacoes`, lida em atendimentos seguintes); a v2 a substitui por
  `registrar_preferencia(campo, valor)` com campos permitidos e nenhum campo de direito
  ou compensação. O `C08` roda em dois atendimentos do mesmo cliente.
- **B9 — Categoria em duas camadas:** `before_model_callback` remove do pedido ao modelo
  as ferramentas não permitidas para a categoria (o modelo nem as vê); `before_tool_callback`
  bloqueia mesmo assim (defesa em profundidade).
- **B10 — Guardrail de entrada em duas camadas:** regras (padrões de injeção, PII do
  cliente) no componente `guardrail_entrada` (N2.2), e o campo `sinais_de_risco` na
  saída da triagem, que só existe com `sequencia` e é usado pelo componente
  `categorias` (N2.6).

### Testes
- **B11 — Matriz.** Testes parametrizados por versão (`pytest --versao v2` ou
  `RANGOJA_VERSAO`); `matriz(arquivo, versoes)` roda o pytest em subprocesso e lê o
  relatório JUnit. Estados: **passa**, **falha**, **não se aplica** (`pytest.skip` com
  motivo).
- **B12 — Rótulos humanos.** 30 respostas rotuladas por tom, por cada apresentador
  separadamente (`evals/rotulos_tom.yaml`); relatar concordância humano×humano (kappa de
  Cohen) e juiz×consenso. É tarefa dos autores, listada nas pendências.
- **D1 — `tests/test_resiliencia.py`** com falhas injetadas; só a v3 passa.
- **D4 — Orçamento `live`:** N = 5 repetições; o NB04 em `live` é para os autores; o
  participante vê as gravações. Estimativa na spec do NB04.

### Casos e dados
- **C1 — Categoria principal única.** Quando houver mais de um problema, a principal é a
  de maior compensação; os demais vão na justificativa (regra da política).
- **C2 — Um pedido por variante de atraso** (5340, 5370, 5420), com horários coerentes.
- **C3 — Nova ferramenta `solicitar_reenvio`.**
- **C4 — `C12` reescrito** como pedido do cliente pelo telefone do entregador.
- **C5 — N2.3 (guardrail de saída)** usa roteiro e é apresentado como defesa em camadas.
- **C6 — `Atendimento.turnos`** guarda cada turno; `atender` roda todos os turnos do caso.

### Conteúdo
- **NB02 reordenado** para que cada componente dependa só dos anteriores: limite e
  aprovação → guardrail de entrada → guardrail de saída → memória → orquestração em
  etapas → categoria → contrato.
- **D2 — N3.6 com duas falhas reais de duplicação:** (a) a ferramenta executa o efeito e
  estoura o tempo, e o modelo chama de novo; (b) a retomada do ADK refaz a chamada
  (comportamento documentado pelo próprio ADK). A idempotência resolve as duas.
- **D3 — Contrato completo** do pacote listado no README.
- **Estado da conversa (N1.5).** Como o ADK já guarda o histórico da sessão, a falha
  "sem estado" é definida como `v1.sem("estado")`: cada turno numa sessão nova, como uma
  API sem sessão. O componente `estado` mantém a sessão e grava `pedido_id`, categoria e
  compensações em `session.state` via `output_key` e ferramentas.
- **Memória como funcionalidade antes de ser risco.** O NB01 ganha N1.7 (`C13`): a
  `memoria_livre` lembra uma preferência entre atendimentos. O NB02 (N2.4) mostra a
  mesma memória sendo envenenada.
- **Recorrência (C07)** é aplicada pelo componente `memoria_segura`, que lê
  `user:reembolsos_30d` num `before_tool_callback`.
- **Relações metamórficas sem violação.** Se a medição em `live` não encontrar violação,
  N4.7 mantém o teste (é o teste certo mesmo passando), relata a taxa medida e ilustra o
  que seria uma violação com um roteiro, dizendo isso.
