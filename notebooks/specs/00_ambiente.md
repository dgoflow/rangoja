# NB00 — Ambiente (`00_ambiente.ipynb`)

**Objetivo.** Garantir, antes do workshop, que o participante consegue rodar todos os
notebooks. Feito em casa; não é apresentado.

**Duração estimada para o participante:** 10 min.
**Depende de:** pacote instalado (`uv sync`), cache e gravações versionados no repositório.

## Seções

| ID | Verifica | Sucesso | Falha → orientação |
|---|---|---|---|
| N0.1 | Python ≥ 3.11 e dependências | `✅ OK` com versões de `google-adk` (1.33.0), `arize-phoenix`, `openinference-instrumentation-google-adk` | link para a seção de problemas do `SETUP.md` |
| N0.2 | Modo `replay`: `atender(v1, caso("C01"))` vindo do cache | `Decisao` impressa; `fonte == "cache"` | cache ausente → `git checkout .cache/ rangoja/gravacoes/` |
| N0.3 | Chave do Gemini (opcional) e uma chamada `live` mínima | `✅ OK` com o ID do modelo configurado | sem chave → aviso: "você pode seguir em `replay`" |
| N0.4 | Phoenix sobe localmente e recebe o trace de N0.2 | link do trace | porta ocupada → instrução; sem Phoenix, os notebooks mostram a trajetória em tabela |
| N0.5 | `adk web` encontra os agentes | comando impresso (`adk web rangoja/versoes`) para rodar no terminal | — |
| N0.6 | `pytest tests/test_orquestracao.py --versao v2` em `replay` | todos passam | reportar a saída |
| N0.7 | Resumo | tabela com ✅/⚠️ por item | — |

**Regra:** só N0.1, N0.2 e N0.6 são bloqueantes. Sem chave ou sem Phoenix, o participante
acompanha em `replay`.

**Verificação:** a célula N0.7 lança `AssertionError` se um item bloqueante falhar.
