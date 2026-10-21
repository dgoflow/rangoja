# Guia do participante

Tudo roda **sem chave de API e sem internet** (modo `replay`): as respostas do modelo vêm de
gravações feitas com um modelo real e de roteiros escritos à mão. A chave só é necessária se
você quiser ver o modelo responder ao vivo.

## Requisitos

- Python 3.11 ou mais novo (testado em 3.12)
- [uv](https://docs.astral.sh/uv/) (ou `pip`)
- Git

## Instalação

```bash
git clone <url-do-repositorio> rangoja && cd rangoja
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,live]"
python -m ipykernel install --user --name rangoja
```

O kernel `rangoja` é o que os notebooks usam. Para ver os traces no Phoenix (opcional):

```bash
uv pip install -e ".[observabilidade]"
```

## Primeiro passo: NB00

```bash
jupyter lab notebooks/00_ambiente.ipynb
```

Escolha o kernel **rangoja** e execute tudo. A tabela da primeira célula mostra modo, modelo,
chave e Phoenix. Se `RANGOJA_MODO` aparecer como `replay`, está tudo certo.

Cada seção dos notebooks abre com `preparar_secao("N2.3")` e roda sozinha: você pode pular
direto para a que quiser.

## Conferir que está tudo funcionando

```bash
pytest tests -m "not live"                         # testes contra a v3
pytest tests --versao v1 -m "not live"             # a mesma bateria contra a v1 (falhas esperadas)
python scripts/verificar_gravacoes.py              # gravações em dia com o código
pytest --nbmake --nbmake-kernel=rangoja notebooks/0*.ipynb   # executa os notebooks (~4 min)
```

## Usando o modelo ao vivo (opcional)

Copie `.env.example` para `.env` e preencha a chave:

```bash
cp .env.example .env
```

| Variável | Para quê | Padrão |
|---|---|---|
| `OPENAI_API_KEY` ou `GOOGLE_API_KEY` | chave do provedor | — |
| `RANGOJA_PROVEDOR` | `openai` ou `gemini` | `openai` se houver chave OpenAI |
| `RANGOJA_MODO` | `replay`, `live` ou `record` | `replay` |
| `RANGOJA_MODELO`, `_FALLBACK`, `_JUIZ` | modelos usados | `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4o` |
| `RANGOJA_REPETICOES` | repetições dos testes estatísticos | `5` |
| `RANGOJA_LIMIAR_ESTABILIDADE` | taxa mínima de acerto | `0.8` |
| `RANGOJA_PHOENIX` | `off` desliga o Phoenix | `on` |

Em `live`, as células de falha continuam usando a gravação (para a lição aparecer sempre);
passe `gravacao=None` a `atender` para ver o modelo de verdade. Em `record`, as respostas novas
são salvas em `rangoja/gravacoes/`. **Isso custa tokens.** `.env` fica fora do git.

## Phoenix

Com o extra `observabilidade` instalado e `RANGOJA_PHOENIX` diferente de `off`, o NB00 sobe o
Phoenix em `http://127.0.0.1:6006` e os atendimentos aparecem no projeto `rangoja`.
Sem o pacote, os notebooks usam a `anatomia` em texto.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `ModuleNotFoundError: rangoja` no notebook | O kernel errado. Escolha `rangoja` e confirme que instalou com `-e` |
| `RespostaAusente` / `RoteiroEsgotado` em replay | Gravação desatualizada: `python scripts/verificar_gravacoes.py` diz qual; regrave com chave (`scripts/gravar_secoes.py --so N1.2/correcao`) |
| Porta 6006 ocupada | `RANGOJA_PHOENIX_PORTA=6007` ou `RANGOJA_PHOENIX=off` |
| Aviso "live sem chave, usando replay" | Falta `OPENAI_API_KEY` no `.env`; sem ela tudo roda em replay |
| `litellm` conflita com `mcp` | Use a versão fixada pelo extra `live` (`litellm==1.82.6`) |
