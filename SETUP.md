# Guia do participante

Tudo roda **sem chave de API e sem internet** (modo `replay`): as respostas do modelo vêm de
gravações feitas com um modelo real e de roteiros escritos à mão. Com a sua chave da OpenAI, você
vê o modelo responder ao vivo (modo `live`); veja [Usando o modelo ao vivo](#usando-o-modelo-ao-vivo).

## Ambientes

| Ambiente | Situação |
|---|---|
| Linux | recomendado |
| Windows com WSL2 (Ubuntu) | recomendado |
| macOS | deve funcionar, não verificado |
| Windows nativo (PowerShell) | não recomendado |

No WSL, clone dentro do Linux (`~/rangoja`), **nunca** em `/mnt/c/...`: ali a instalação e o SQLite
ficam lentos e podem dar erro de permissão. No Windows sem WSL, `wsl --install` instala o Ubuntu
(pede reinício).

## Requisitos

- Python 3.11 ou mais novo (testado em 3.12; o `uv` baixa o 3.12 se faltar)
- [uv](https://docs.astral.sh/uv/) (ou `pip`)
- Git

## Instalação

```bash
git clone https://github.com/dgoflow/rangoja.git ~/rangoja && cd ~/rangoja
uv sync --extra dev --extra live
uv run python -m ipykernel install --user --name rangoja
```

O `uv sync` cria o ambiente com o Python 3.12 (baixa se faltar) e instala exatamente as versões de
`uv.lock`, as mesmas que o CI testa. Sem `source .venv/bin/activate`: os comandos rodam com `uv run`.

O kernel `rangoja` é o que os notebooks usam. O registro é **por usuário**, não por pasta: se você
tiver mais de um clone, vale o último em que rodou o `ipykernel install`. Rode-o de novo no clone que
estiver usando.

## Primeiro passo: NB00

```bash
uv run jupyter lab notebooks/00_ambiente.ipynb
```

Escolha o kernel **rangoja** e execute tudo, de cima para baixo. Em qualquer notebook, a primeira
célula de código é a **preparação**: execute-a uma vez antes de rodar qualquer seção isolada (sem ela
aparece `NameError: name 'verificar' is not defined`).

A tabela da primeira célula mostra modo, modelo, chave e Phoenix. A linha da chave diz:

| Chave de API | Significado |
|---|---|
| `não (use replay)` | sem chave: tudo roda em replay, e está tudo certo |
| `sim, validada` | a OpenAI aceitou a chave |
| `sim, mas a OpenAI a recusou` | a chave está errada ou foi revogada |
| `sim, não validada (sem rede?)` | a OpenAI não respondeu a tempo; a chave pode estar certa |

Se N0.1, N0.2 e N0.6 passaram, você está pronto. Cada seção dos notebooks abre com
`preparar_secao("N2.3")` e roda sozinha: você pode pular direto para a que quiser.

## Usando o modelo ao vivo

Há dois jeitos de informar a chave. **Cada notebook roda num kernel próprio**, e é por isso que eles
diferem.

**Pela célula N0.3 do NB00 (mais simples).** Execute a célula e cole a chave quando ela pedir: a
entrada é oculta e a chave é validada na hora, sem gastar tokens. O modo `live` liga para aquele
notebook. A célula pergunta se você quer **salvar no `.env`**; responda `s` para os outros notebooks
também a usarem (o arquivo fica fora do git, com permissão só para você). Se já houver chave, a N0.3
só liga o modo `live`.

**Pelo `.env`.** Copie o exemplo e preencha:

```bash
cp .env.example .env
```

Ponha a chave em `OPENAI_API_KEY` e, para ir ao vivo, `RANGOJA_MODO=live`. O `.env` é lido quando o
kernel começa: **se você editá-lo com o notebook aberto, reinicie o kernel** (Kernel → Restart Kernel)
e rode a primeira célula de novo.

| Variável | Para quê | Padrão |
|---|---|---|
| `OPENAI_API_KEY` | chave da OpenAI | — |
| `RANGOJA_MODO` | `replay`, `live` ou `record` | `replay` |
| `RANGOJA_MODELO` | modelo usado ao vivo (também pelo agente montado à mão na N1.1) | `gpt-4o-mini` |
| `RANGOJA_MODELO_FALLBACK`, `_JUIZ` | modelo secundário e juiz | `gpt-4.1-mini`, `gpt-4o` |
| `RANGOJA_REPETICOES` | repetições dos testes estatísticos | `5` |
| `RANGOJA_LIMIAR_ESTABILIDADE` | taxa mínima de acerto | `0.8` |
| `RANGOJA_PHOENIX` | `off` desliga o Phoenix | `on` |

**O que muda em `live`.** O agente que a N1.1 monta à mão chama o modelo de `RANGOJA_MODELO` de
verdade: a resposta varia entre execuções. As células de falha que usam `atender(..., gravacao=...)`
continuam usando a gravação, para a lição aparecer sempre; passe `gravacao=None` a `atender` para ver
o modelo de verdade. Em `record`, as respostas novas são salvas em `rangoja/gravacoes/`.
**Isso custa tokens**; prefira uma chave com limite de gasto baixo.

Para rodar os testes com o modelo real (estabilidade da trajetória e relações metamórficas), é preciso a chave **e** o modo `live`; sem os dois, eles aparecem como `s` (pulados) e `-rs` mostra o motivo:

```bash
RANGOJA_MODO=live uv run pytest tests -m live -rs
```

Cada teste repete os casos várias vezes (`RANGOJA_REPETICOES`, padrão 5) e **custa tokens**. Com o modelo real o resultado varia entre execuções, e um teste de estabilidade pode falhar sem que haja um defeito novo.

## Conferir que está tudo funcionando

```bash
uv run pytest tests -m "not live"                         # testes contra a v3
uv run pytest tests --versao v1 -m "not live"             # a mesma bateria contra a v1 (falhas esperadas)
uv run python scripts/verificar_gravacoes.py              # gravações em dia com o código
uv run pytest --nbmake --nbmake-kernel=rangoja notebooks/0*.ipynb   # executa os notebooks (~4 min)
```

## Atualizar o repositório

Executar um notebook grava as suas saídas no arquivo, e o `git pull` recusa sobrescrevê-lo. Guarde as
saídas antes:

```bash
git stash push -m "minhas saidas" -- notebooks/ && git pull --ff-only
```

Depois reinicie o kernel dos notebooks abertos. Para atualizar o ambiente depois de um `git pull`, rode
`uv sync --extra dev --extra live` de novo.

## Phoenix

O Phoenix já vem na instalação. A primeira célula do NB00 sobe o servidor em `http://127.0.0.1:6006`,
e os atendimentos aparecem no projeto `rangoja`. Com `RANGOJA_PHOENIX=off`, ou se a porta 6006 estiver
ocupada, os notebooks usam a `anatomia` em texto, sem perda de conteúdo.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `ModuleNotFoundError: rangoja` no notebook | O kernel errado. Escolha `rangoja` e confirme que instalou com `-e` no clone que está usando |
| O notebook usa o código de outro clone | O kernel `rangoja` aponta para o último clone instalado: rode `uv run python -m ipykernel install --user --name rangoja` neste |
| A tabela diz `chave de API: não` mas o `.env` tem a chave | O kernel abriu antes de você editar o `.env`: reinicie o kernel e rode a primeira célula |
| `chave de API: sim, mas a OpenAI a recusou` | Confira se copiou a chave inteira; ou apague-a do `.env`, reinicie o kernel e cole outra na N0.3 |
| A N1.1 mostra `modelo: gravação` com a chave configurada | O kernel está em `replay`: ponha `RANGOJA_MODO=live` no `.env` (ou use a N0.3) e reinicie o kernel |
| O NB01 pede a chave de novo depois da N0.3 | Cada notebook tem seu kernel: na N0.3, responda `s` para salvar no `.env` |
| `git pull` diz *Your local changes would be overwritten* | Veja [Atualizar o repositório](#atualizar-o-repositório) |
| Aviso vermelho `IProgress not found` | Falta `ipywidgets`: rode `uv sync --extra dev --extra live` e reinicie o kernel |
| `RespostaAusente` / `RoteiroEsgotado` em replay | Gravação desatualizada: `uv run python scripts/verificar_gravacoes.py` diz qual; regrave com chave (`scripts/gravar_secoes.py --so N1.2/correcao`) |
| Porta 6006 ocupada | `RANGOJA_PHOENIX_PORTA=6007` ou `RANGOJA_PHOENIX=off` |
| `litellm` conflita com `mcp` | Use a versão fixada pelo extra `live` (`litellm==1.82.6`) |
