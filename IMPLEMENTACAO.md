# Status da implementação do pacote `rangoja`

Especificação: [specs/pacote/](specs/pacote/README.md) e [notebooks/](notebooks/README.md). Este arquivo registra o que está
implementado, o que falta, o que foi medido com o modelo real e os desvios da spec.

## Implementado

- **Dados e domínio:** 12 pedidos, 9 clientes, 2 entregadores, política em markdown, 20 casos (`casos.yaml`); `tipos`, `politica`, `armazem` (SQLite), 9 ferramentas com efeito real.
- **Pilha do modelo** (`modelo/`): fallback → retry → injeção de falhas → fonte (roteiro, gravação nomeada, cache, modelo ao vivo). Provedor OpenAI via `LiteLlm` do ADK. Modos `replay`, `live`, `record`.
- **Controle e resiliência** (`controle.py`): guardrails de entrada e saída, categorias, consulta determinística, contrato, golpe, recorrência, limites, erros estruturados.
- **Componentes e versões** (`agentes.py`, `versoes.py`): 19 componentes com dependências; `montar`, `sem`/`com`, `resolver`; v0–v3, também com nomes que dizem o que são (`v0_so_prompt`, `v1_agente`, `v2_controlado`, `v3_robusto`).
- **Execução** (`execucao.py`): `atender`, `atender_caso` (a mesma chamada com nomes que se leem como frase), `continuar`, `aprovar`, `recusar`, `expirar_pendencias`, `reiniciar_runner`, `estado_persistido`.
- **Seções e notebooks:** `secoes.py` (21 seções), `notebook.py` (`preparar_ambiente`, `preparar_secao`, `mostrar`, `comparar`, `afirmar`, `esperar`, `resumo`, `amostra`, `matriz`; `verificar` e `verificar_falha` seguem como nomes antigos), `observabilidade.py` (Phoenix + `anatomia` em texto).
- **Notebooks NB00 a NB04** em `notebooks/`, com saídas salvas e o kernel `rangoja` nos metadados. Geradores em `scripts/gerar_nb*.py`; execução em `scripts/executar_notebooks.py` (`RANGOJA_KERNEL` troca o kernel). Todos usam `atender_caso`, `afirmar`/`esperar` e `comparar`; 17 células `# 🎯 EXPERIMENTE` comentadas, do NB01 ao NB04, todas conferidas em replay, menos a da N4.8, que exige `live` (a temperatura chega ao modelo; `test_modos.py` confere). As conferências que dependem do modelo usam `esperar`, então em `live` viram ⚠️ em vez de interromper o notebook. `pytest --nbmake` passa os 5 principais e os 3 extras em replay (cerca de 40 s).
- **Avaliação** (`avaliacao/`): 11 avaliadores programáticos + 2 globais, relações metamórficas (invariância e monotonicidade), `evals/golden.yaml`.
- **Gravações com o modelo real** (`gravacoes/`): 20 casos do golden na v3 (relatórios), 4 falhas da rodada exploratória e 16 execuções de seção, em arquivos nomeados que o replay reproduz sem chave.
- **Scripts:** `gravar.py`, `rodada_exploratoria.py`, `gravar_secoes.py`, `gerar_golden.py`, `verificar_gravacoes.py` (confere em replay se cada gravação ainda serve ao código).
- **Extras** (`notebooks/extras/`): `x1_memoria_pesquisavel` (`InMemoryMemoryService` + `load_memory`; política bruta × fatos verificados), `x2_conversas_longas` (janela, resumo, estado estruturado), `x3_dados_sinteticos` (persona × cenário, dedup, filtro, variantes metamórficas) e `x5_execucao_duravel.md` (texto). O x4 (Langfuse) da spec original foi removido: o backend de observabilidade do material é só o Phoenix. Helpers em `rangoja/extras.py`; gerador em `scripts/gerar_extras.py`. Limites: em x1 o modelo é roteirizado (verifica-se o que a memória guarda e devolve, não a redação); em x2 a conversa de 20 turnos e o resumo são escritos à mão e os tokens são estimados (1 token ≈ 4 caracteres); em x3 as reclamações vêm de modelos de frase, não de um modelo de linguagem, e o classificador de referência é por palavras-chave.
- **CI** (`.github/workflows/`): `ci.yml` (instalação com `uv sync --locked`, ruff, gravações em dia, `pytest -m "not live"` na v3, `test_regressao_detectada` e os 8 notebooks em replay) e `avaliacao.yml` (testes `live`, semanal e manual, segredo `OPENAI_API_KEY`). Instalação limpa com `uv sync --locked` verificada em macOS (ruff, gravações, 94 testes e os 8 notebooks). Os 8 notebooks também foram executados em `live` com um modelo falso que nunca segue o roteiro: nenhum é interrompido (o que depende do modelo vira ⚠️).
- **Ambiente:** `uv.lock` com as versões travadas; `.devcontainer/` para GitHub Codespaces e VS Code com Docker (configuração não executada num contêiner nesta revisão).
- **Docs:** `README.md`, `SETUP.md`, `ROTEIRO.md` (com o diagrama do agente da v3) e `palestra/apresentacao.md` (roteiro da apresentação).

Testes (`tests/`, suíte completa, sem `live`, modelo roteirizado):

| Versão | Passa | Falha | Skip | Observação |
|---|---|---|---|---|
| v3 | 94 | 0 | 2 (live) | |
| v2 | 88 | 6 | 2 | falha só nas resiliências |
| v1 | 75 | 19 | 2 | falha no controle |
| v0 | 58 | 1 | 37 | sem ferramentas; vaza PII na resposta |

## Medido com o modelo real (gpt-4o-mini, via OpenAI)

- **Correção de método:** a primeira rodada exploratória reaproveitava o cache nas 10 tentativas, então só a primeira resposta do modelo variava. Agora `record` nunca lê o cache. Com amostragem real, a falha do golpe (N2.6) passou de 1/10 para 5/10; as demais não mudaram.
- **Rodada exploratória** (`gravacoes/RELATORIO.md`, v1, 10 tentativas): N2.1 (reembolso acima do limite) 10/10; N2.2 (injeção) 10/10; N2.4 C07 (recorrência) 10/10; N2.4 C08 (memória envenenada) 10/10; N2.6 (golpe) 5/10; **N2.3 (PII), N2.5 (sem consulta) e N2.7 (sem pedido) 0/10**. Estas três são **roteiro** nos notebooks, e as células dizem isso.
- **Golden v3** (`gravacoes/v3/*.json`): 10 dos 20 casos sem nenhuma regra reprovada. Os resultados variam entre execuções. Desvios frequentes: o modelo escolhe `voucher` ou `escalar` onde se esperava `reembolso`, ou classifica o golpe como outra categoria.
- **Invariância:** com amostragem real, o grupo C01 violou a relação (gíria, ruído ou valor ausente), e o resultado muda de uma execução para outra.
- **Gravações de seção:** N1.2 correção (consulta o pedido?) **0/6**: com a política colada na instrução, o modelo não consultou o pedido em nenhuma execução. N1.5 correção 6/6; N1.6 5/6 e 6/6; N1.7 correção (menciona a portaria) 1/6.

## Não implementado

- Juiz de tom (`avaliacao/juiz.py`), concordância e `evals/rotulos_tom.yaml` (depende de rotulagem humana).
- `evals/trajetoria.evalset.json` e `test_config.json` do `AgentEvaluator` (formato não verificado no ADK 1.33).
- Medição de temperatura (N4.8): a célula EXPERIMENTE (`# requer: live`) mede com a chave de quem roda, mas os números não estão no material. Métricas agregadas do Phoenix (N3.7).
- Gravações com outro modelo além do gpt-4o-mini: os números citados valem para ele.
- `scripts/gerar_evalset.py`.
- Testes de `expirar_pendencias` isolado e de `continuar` na memória entre atendimentos (C13), fora dos notebooks.
- `Atendimento.trace_url` fica nulo; o link do Phoenix é a URL do projeto.

## Desvios da spec (e por quê)

1. **Aprovação humana por fila no armazém, não por `require_confirmation` do ADK.** Com a confirmação dentro do `SequentialAgent`, a retomada executou a resposta antes de a decisão existir. A fila é determinística e sobrevive à queda do runner.
2. **Valores da decisão como `float`** (o ADK serializa a saída estruturada com `json` padrão e falha com `Decimal`).
3. **Consulta determinística do pedido** antes da resolução, na sequência.
4. **Recorrência lida do armazém**, não de `user:reembolsos_30d`.
5. **C11 usa o pedido 4822** (4821 já é o de C01); **C05 pede o pedido inteiro** (R$ 70); **C08 e C13 tiveram a expectativa ajustada** (C13 agora espera que o sistema peça o pedido; C08 só verifica que o direito alegado não vai para a memória).
6. **Filtro de ferramentas** esconde declarações, mas mantém a ferramenta em `tools_dict`; ocultar quebrava o ADK com "tool not found".
7. **Persistência (v3):** `SqliteSessionService` por caso.
8. **Guardrail de entrada fora do escopo** devolve uma saída válida para o agente que roda (Triagem ou Decisao), não texto livre.
9. **Contrato limpa a interrupção** quando a mensagem seguinte traz pedido válido (sem isso, a conversa de vários turnos travava).
10. **Provedor:** spec previa Gemini e "sem LiteLLM". A chave é da OpenAI, então o caminho ao vivo usa o `LiteLlm` do ADK, fixado em `1.82.6` (a 1.106 exige um `mcp` mais novo que o do ADK 1.33).
11. **Reparo de saída estruturada no caminho ao vivo:** o ADK entrega a decisão por uma ferramenta (`set_model_response`); o gpt-4o-mini às vezes responde em prosa. A camada ao vivo pede de novo (até 2 vezes). Sem isso, o C11 na v1 falhava em 3 de 3 execuções.
12. **Gravações nomeadas**, não só cache: a cadeia de respostas do modelo de uma execução, em JSON, lida por `Roteiro.de_arquivo`. `scripts/gravar_secoes.py` escolhe, com um critério, a primeira execução que mostra a lição e registra a taxa em `amostra`.
13. **Observabilidade:** o exportador é OTLP/HTTP direto (não `phoenix.otel`, que exige outra versão do SDK de OpenTelemetry que o ADK fixa). Foi preciso: `openinference-instrumentation-google-adk<1` (a 1.x só instrumenta ADK ≥ 2.10), `fastmcp` (o Phoenix 20 importa o cliente) e o conjunto `opentelemetry-*` alinhado em `1.41.1`. Verificado: 13 spans de um atendimento chegam ao projeto `rangoja`.
14. **Guardrail de saída** também limpa a saída estruturada (`mensagem_ao_cliente`), não só texto.
15. **Notebooks:** o texto das lições é adaptado ao que as gravações mostram. Onde o modelo real não reproduz a lição esperada (ex.: N1.2), o notebook diz isso.
16. **O cache do modelo (`.cache/`) não é versionado**, ao contrário do que a spec previa. São cerca de 900 arquivos, subproduto das rodadas de gravação, e nada nos notebooks nem nos testes em `replay` os usa: tudo vem das gravações nomeadas em `rangoja/gravacoes/` e dos roteiros. Verificado sem o cache: gravações em dia, os testes e os notebooks passam. O cache só é lido em `replay`.
17. **`live` ignora as gravações.** A spec previa que as células de falha continuassem usando a gravação em `live`. Agora, em `live` e `record`, o modelo responde de verdade em todas as células e a gravação vira só referência (`amostra`); os roteiros continuam valendo. Por isso a apresentação roda em `replay` na sala.
18. **Phoenix e a instrumentação são dependências principais**, não um extra `observabilidade`: o NB00 já os usa.
19. **Versões não são pacotes de agente** (`rangoja/versoes/vN/agent.py` com `root_agent`): os notebooks usam o `Runner` como biblioteca, e `adk web`/`adk eval` ficaram fora do material.
