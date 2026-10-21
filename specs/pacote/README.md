# Pacote `rangoja` — especificação

> Status: **proposta v0.1**. Implementa o contrato definido em
> [`notebooks/README.md`](../../notebooks/README.md). Decisões herdadas:
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
  config.py          leitura de .env e variáveis RANGOJA_*
  tipos.py           modelos Pydantic do domínio (Pedido, Cliente, Decisao, Triagem, Caso…)
  dados/             pedidos.json, clientes.json, entregadores.json,
                     politica_reembolso.md, casos.yaml
  politica.py        regras da política em código
  armazem.py         estado mutável do "sistema" (SQLite): reembolsos, cupons, tickets…
  ferramentas.py     ferramentas expostas ao agente
  agentes/           agente_unico.py, triagem.py, resolucao.py, resposta.py
    instrucoes/      fragmentos de instrução em markdown, por componente
  controle/          aprovacao.py, guardrails.py, memoria.py, categorias.py, contrato.py
  resiliencia/       erros.py, retry.py, fallback.py, limites.py, persistencia.py, idempotencia.py
  modelo/            pilha.py, fonte.py, cache.py, gravacao.py, roteiro.py, injecao.py, gemini.py
  componentes.py     registro de componentes e a classe Montagem
  versoes/           __init__.py (v0…v3, montar), v0/agent.py … v3/agent.py
  agent.py           root_agent = v3
  execucao.py        atender, continuar, aprovar, recusar, expirar_pendencias, reiniciar_runner
  trajetoria.py      Chamada e funções de trajetória
  falhas.py          injeção de falhas
  relogio.py         relógio controlável
  secoes.py          registro das seções dos notebooks
  notebook.py        helpers de notebook
  observabilidade.py Phoenix + OpenInference
  avaliacao/         programaticos.py, juiz.py, concordancia.py, metamorficas.py
  roteiros/          roteiros (respostas escritas à mão) por seção
  gravacoes/         gravações nomeadas por seção (JSON)
  scripts/           gravar.py, rodada_exploratoria.py, gerar_golden.py,
                     gerar_evalset.py, verificar_gravacoes.py
tests/               conftest.py, roteiros/, test_*.py
evals/               golden.yaml, trajetoria.evalset.json, test_config.json, rotulos_tom.yaml
.cache/modelo/       cache de respostas (versionado)
notebooks/
.github/workflows/   ci.yml, avaliacao.yml
pyproject.toml  uv.lock  .env.example  SETUP.md  README.md
```

## Especificações por área

| Arquivo | Conteúdo |
|---|---|
| [01_dados_politica_ferramentas.md](01_dados_politica_ferramentas.md) | `tipos`, dados, `politica`, `armazem`, `ferramentas`, `casos.yaml` |
| [02_modelo.md](02_modelo.md) | Pilha do modelo: fontes (cache, gravação, roteiro, Gemini), injeção, retry, fallback, modos |
| [03_componentes_versoes.md](03_componentes_versoes.md) | Componentes, agentes, callbacks, `montar`, versões v0–v3 |
| [04_execucao_secoes_notebook.md](04_execucao_secoes_notebook.md) | `execucao`, `Atendimento`, aprovação, relógio, falhas, trajetória, seções, helpers de notebook, observabilidade |
| [05_testes_avaliacao_ci.md](05_testes_avaliacao_ci.md) | Testes, avaliação, evals, scripts, CI, `SETUP.md` |

## Dependências (`pyproject.toml`)

| Grupo | Pacotes |
|---|---|
| principal | `python >= 3.11`, `google-adk == 1.33.0`, `pydantic >= 2`, `pyyaml`, `python-dotenv`, `arize-phoenix`, `openinference-instrumentation-google-adk`, `pandas`, `pygments` |
| dev | `pytest`, `pytest-asyncio`, `nbmake`, `jupyter`, `ruff` |

Sem LiteLLM, BAML, DSPy, ChromaDB ou Temporal.

## Configuração (`.env.example`)

| Variável | Padrão | Uso |
|---|---|---|
| `GOOGLE_API_KEY` | — | Gemini via AI Studio; só em `live`/`record` |
| `RANGOJA_MODO` | `replay` | `replay`, `live`, `record` |
| `RANGOJA_MODELO` | a fixar | modelo primário do agente |
| `RANGOJA_MODELO_FALLBACK` | a fixar | modelo secundário |
| `RANGOJA_MODELO_JUIZ` | a fixar | modelo do juiz (outro tamanho/família) |
| `RANGOJA_PHOENIX` | `on` | liga a observabilidade |
| `RANGOJA_PHOENIX_PORTA` | `6006` | porta do Phoenix local |
| `RANGOJA_REPETICOES` | `5` | repetições nos testes estatísticos |
| `RANGOJA_LIMIAR_ESTABILIDADE` | `0.8` | limiar dos testes estatísticos |

Os IDs de modelo são fixados na implementação (modelos Gemini disponíveis no AI Studio
na data) e gravados nos metadados de cada gravação.

## Ordem de implementação

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
  `verificar` passando (`pytest --nbmake notebooks/`).
- `pytest tests/ --versao v3` (determinísticos) passa; a matriz do NB04 reproduz o padrão
  esperado em cada spec de seção.
- `scripts/verificar_gravacoes.py` não acusa gravação desatualizada.
- `adk web rangoja/versoes` lista v0–v3 e cada uma atende `C01`.
- Nenhum dado real: telefones, placas e nomes são fictícios.
