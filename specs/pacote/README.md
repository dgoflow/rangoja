# Pacote `rangoja` — especificação

> Status: **implementada.** Este README descreve o pacote como ele é. Os arquivos 01–05 são a
> proposta original (v0.1) e foram mantidos como registro: onde a implementação diverge deles
> (provedor OpenAI via `LiteLlm` em vez de Gemini, módulos agrupados, `live` sem gravações, sem `adk web`),
> vale o que está aqui e em [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).
> Contrato com os notebooks: [`notebooks/README.md`](../../notebooks/README.md). Decisões herdadas:
> [`notebooks/specs/decisoes.md`](../../notebooks/specs/decisoes.md).

O pacote `rangoja` é o sistema de atendimento do app de delivery fictício RangoJá, em
quatro versões (v0–v3), mais a infraestrutura que torna o material do workshop
reproduzível: cache e gravações de respostas do modelo, injeção de falhas, isolamento por
seção e helpers para notebooks e testes.

## Princípios

1. **Os notebooks dependem só do contrato.** Tudo que está fora de
   `notebooks/README.md#contrato-com-o-pacote-rangoja` pode mudar sem quebrar notebook.
2. **Componentes pequenos e legíveis.** Cada componente é um módulo curto, exibido por
   `mostrar()`. Código de infraestrutura (cache, gravação, execução) fica separado e não
   é exibido em aula.
3. **`replay` é o modo padrão e não usa rede.** Notebooks e testes determinísticos rodam
   sem chave de API.
4. **Regras de domínio em código.** A política existe como texto (lido pelo modelo) e
   como funções (usadas por callbacks, ferramentas e testes). Os dois ficam no mesmo
   diretório e um teste garante que concordam.
5. **Português** em nomes de módulos, funções, campos e mensagens; APIs do ADK com os
   nomes originais.

## Estrutura

```
rangoja/
  __init__.py
  config.py          leitura de .env, variáveis RANGOJA_*, chave e modo (N0.3)
  tipos.py           modelos Pydantic do domínio (Pedido, Cliente, Decisao, Triagem, Caso…)
  dados/             pedidos.json, clientes.json, entregadores.json,
                     politica_reembolso.md, casos.yaml
  dados.py, casos.py leitura dos dados e dos casos
  politica.py        regras da política em código
  armazem.py         estado mutável do "sistema" (SQLite): reembolsos, pendências, cupons, tickets…
  ferramentas.py     ferramentas expostas ao agente (com as variantes enxuta, com aprovação, idempotente)
  controle.py        callbacks de controle e resiliência: guardrails, categorias, consulta em código,
                     contrato, recorrência, limites, erro estruturado
  agentes.py         montagem dos agentes ADK a partir dos componentes de uma versão
  versoes.py         componentes, dependências, `montar`, v0–v3 e os nomes v0_so_prompt…v3_robusto
  modelo/            pilha.py (fallback → retry → falhas → fonte), contexto.py, gravacao.py, roteiro.py
  execucao.py        atender, atender_caso, continuar, aprovar, recusar, expirar_pendencias, reiniciar_runner
  trajetoria.py      Chamada e funções de trajetória
  falhas.py          injeção de falhas
  relogio.py         relógio controlável
  roteiros.py        respostas escritas à mão, por seção
  secoes.py          registro das seções dos notebooks
  notebook.py        helpers de notebook (preparar_secao, comparar, afirmar, esperar, resumo, matriz…)
  observabilidade.py Phoenix (OTLP/HTTP) + `anatomia` em texto
  extras.py          helpers dos notebooks extras
  avaliacao/         programaticos.py, metamorficas.py
  gravacoes/         gravações nomeadas por seção (JSON) e relatórios do golden na v3
scripts/             gravar.py, gravar_secoes.py, rodada_exploratoria.py, gerar_golden.py,
                     gerar_nb*.py, gerar_extras.py, executar_notebooks.py, verificar_gravacoes.py
tests/               conftest.py, cenarios*.py, test_*.py
evals/               golden.yaml
notebooks/           NB00–NB04, extras/, specs/
palestra/            roteiro da apresentação
.devcontainer/       ambiente para Codespaces e VS Code com Docker
.github/workflows/   ci.yml, avaliacao.yml
pyproject.toml  uv.lock  .env.example  SETUP.md  README.md  ROTEIRO.md  IMPLEMENTACAO.md
```

O cache de respostas do modelo (`.cache/`) não é versionado: nada em `replay` depende dele.

## Especificações por área

| Arquivo | Conteúdo |
|---|---|
| [01_dados_politica_ferramentas.md](01_dados_politica_ferramentas.md) | `tipos`, dados, `politica`, `armazem`, `ferramentas`, `casos.yaml` |
| [02_modelo.md](02_modelo.md) | Pilha do modelo: fontes (cache, gravação, roteiro, modelo ao vivo), injeção, retry, fallback, modos |
| [03_componentes_versoes.md](03_componentes_versoes.md) | Componentes, agentes, callbacks, `montar`, versões v0–v3 |
| [04_execucao_secoes_notebook.md](04_execucao_secoes_notebook.md) | `execucao`, `Atendimento`, aprovação, relógio, falhas, trajetória, seções, helpers de notebook, observabilidade |
| [05_testes_avaliacao_ci.md](05_testes_avaliacao_ci.md) | Testes, avaliação, evals, scripts, CI, `SETUP.md` |

## Dependências (`pyproject.toml`)

| Grupo | Pacotes |
|---|---|
| principal | `python >= 3.11`, `google-adk == 1.33.0`, `pydantic >= 2`, `pyyaml`, `python-dotenv`, `arize-phoenix`, `openinference-instrumentation-google-adk < 1`, `fastmcp` |
| dev | `pytest`, `pytest-asyncio`, `nbmake`, `ruff`, `jupyterlab`, `ipywidgets` |
| live | `litellm == 1.82.6` (o `LiteLlm` do ADK, para os modelos da OpenAI) |

As versões exatas ficam travadas no `uv.lock` (`uv sync --locked`). Sem BAML, DSPy, ChromaDB ou Temporal.

## Configuração (`.env.example`)

| Variável | Padrão | Uso |
|---|---|---|
| `OPENAI_API_KEY` | — | modelos da OpenAI via `LiteLlm`; só em `live`/`record` |
| `RANGOJA_MODO` | `replay` | `replay`, `live`, `record` |
| `RANGOJA_MODELO` | `gpt-4o-mini` | modelo primário do agente |
| `RANGOJA_MODELO_FALLBACK` | `gpt-4.1-mini` | modelo secundário |
| `RANGOJA_MODELO_JUIZ` | `gpt-4o` | modelo do juiz (outro tamanho/família) |
| `RANGOJA_PHOENIX` | `on` | liga a observabilidade |
| `RANGOJA_PHOENIX_PORTA` | `6006` | porta do Phoenix local |
| `RANGOJA_REPETICOES` | `5` | repetições nos testes estatísticos |
| `RANGOJA_LIMIAR_ESTABILIDADE` | `0.8` | limiar dos testes estatísticos |

O modelo de cada gravação fica nos metadados dela (`modelo`, `gravada_em`); todas as gravações
atuais são do gpt-4o-mini.

## Ordem de implementação (histórico)

A ordem seguida na construção; os nomes de módulo são os da proposta original.

1. `tipos`, dados, `politica`, `armazem`, `ferramentas`, `casos.yaml` + testes unitários.
2. `modelo/` (pilha completa) + `relogio` + `falhas`.
3. `componentes`, `agentes`, `controle`, `resiliencia`, `versoes`.
4. `execucao`, `trajetoria`, `secoes`, `notebook`, `observabilidade`.
5. Roteiros e testes determinísticos (`test_orquestracao`, `test_resiliencia`,
   programáticos de `test_qualidade`).
6. `scripts/rodada_exploratoria.py` em `live`; registrar o resultado em
   `notebooks/specs/casos.md` e trocar por roteiro as falhas não obtidas.
7. `scripts/gravar.py` em `record` para cache e gravações.
8. Notebooks 00 → 04, extras.
9. CI, `SETUP.md`, `README.md`.

## Critérios de pronto

- Todo notebook roda do início ao fim em `replay`, sem chave, com todas as células
  `afirmar`/`esperar` passando (`pytest --nbmake notebooks/`).
- `pytest tests/ --versao v3` (determinísticos) passa; a matriz do NB04 reproduz o padrão
  esperado em cada spec de seção.
- `scripts/verificar_gravacoes.py` não acusa gravação desatualizada.
- Nenhum dado real: telefones, placas e nomes são fictícios.
