# RangoJá — do prompt ao agente robusto

[![ci](https://github.com/dgoflow/rangoja/actions/workflows/ci.yml/badge.svg)](https://github.com/dgoflow/rangoja/actions/workflows/ci.yml)

Material do workshop **Além do Prompt: Construindo Sistemas Agênticos Robustos** (AI Brasil
Experience 2026). O caso é o atendimento de um app de delivery fictício, o RangoJá, construído
com [Google ADK](https://google.github.io/adk-docs/) 1.33. Quatro versões do mesmo agente
mostram, uma falha de cada vez, o que separa um prompt de um sistema que se pode confiar.

| Versão | O que tem | Pergunta que responde |
|---|---|---|
| `v0` (`v0_so_prompt`) | só prompt, com a política colada | Funciona? |
| `v1` (`v1_agente`) | ferramentas, saída estruturada, estado, contexto enxuto, memória do cliente | O que separa um prompt de um agente? |
| `v2` (`v2_controlado`) | aprovação humana, guardrails, memória segura, sequência, categorias, contrato | Como impedir o que o agente não deve fazer? |
| `v3` (`v3_robusto`) | erros estruturados, retry e fallback, limites, persistência, idempotência | O que acontece quando algo dá errado? |

Cada capacidade é um **componente** pequeno com nome; uma versão é uma montagem deles
(`v2_controlado.sem("contrato")`, `montar(v1_agente, com=["aprovacao"])`), e `comparar(antes, depois)`
mostra o que muda de uma para a outra. O modelo propõe, o código autoriza. O desenho do agente da v3, com
cada camada e a seção que a introduz, está no [ROTEIRO.md](ROTEIRO.md#como-o-agente-da-v3-roda).

## Notebooks

| Notebook | Tema |
|---|---|
| [`00_ambiente`](notebooks/00_ambiente.ipynb) | Meu ambiente funciona? |
| [`01_do_prompt_ao_agente`](notebooks/01_do_prompt_ao_agente.ipynb) | v0 → v1: ferramentas, schema, estado, contexto, memória |
| [`02_controle`](notebooks/02_controle.ipynb) | v1 → v2: aprovação, guardrails, memória segura, sequência, contrato |
| [`03_falhas_e_observabilidade`](notebooks/03_falhas_e_observabilidade.ipynb) | v2 → v3: falhas, retry, limites, persistência, idempotência, traces |
| [`04_testes_e_avaliacao`](notebooks/04_testes_e_avaliacao.ipynb) | testes por versão, avaliação, golden, testes metamórficos |

Extras opcionais em [`notebooks/extras/`](notebooks/extras/): memória pesquisável, conversas longas, dados sintéticos e um texto sobre execução durável.

Os notebooks são independentes entre si e cada seção roda sozinha. Estão com as saídas salvas
e executam **sem chave de API**: as falhas vêm de gravações de um modelo real (gpt-4o-mini) ou,
quando o modelo real não errou, de roteiros escritos à mão. As células dizem qual é qual. Com a sua
chave, o modo `live` faz o modelo responder de verdade (veja o [SETUP.md](SETUP.md#usando-o-modelo-ao-vivo)).
As seções do NB01 ao NB04 trazem células `# 🎯 EXPERIMENTE` com uma variação para você tentar.

Para uma visão guiada do que cada notebook ensina, leia o [ROTEIRO.md](ROTEIRO.md).

## Como começar

Veja o [SETUP.md](SETUP.md). Em resumo, com o [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev --extra live
uv run python -m ipykernel install --user --name rangoja
uv run jupyter lab notebooks/00_ambiente.ipynb
```

Sem instalar nada: abra o repositório no GitHub Codespaces; o [`.devcontainer/`](.devcontainer/devcontainer.json)
faz a instalação.

## Estrutura

```
rangoja/      pacote: dados, política, ferramentas, agentes, versões, modelo, avaliação
notebooks/    NB00–NB04 e as especificações (notebooks/specs)
tests/        a mesma bateria roda contra qualquer versão: uv run pytest --versao v1
evals/        golden dataset gerado dos casos
scripts/      gravação, geração dos notebooks (os .ipynb são gerados: edite os scripts), verificação das gravações
specs/        especificação do pacote
palestra/     roteiro da apresentação (para quem apresenta)
```

## Resultados honestos

O que foi medido com o modelo real, o que é roteiro e o que não foi implementado estão em
[IMPLEMENTACAO.md](IMPLEMENTACAO.md). Os resultados com modelo real variam entre execuções.

## Licença

[MIT](LICENSE).
