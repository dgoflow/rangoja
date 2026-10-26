# RangoJá — do prompt ao agente robusto

[![ci](https://github.com/dgoflow/rangoja/actions/workflows/ci.yml/badge.svg)](https://github.com/dgoflow/rangoja/actions/workflows/ci.yml)

Material do workshop **Além do Prompt: Construindo Sistemas Agênticos Robustos** (AI Brasil
Experience 2026). O caso é o atendimento de um app de delivery fictício, o RangoJá, construído
com [Google ADK](https://google.github.io/adk-docs/) 1.33. Quatro versões do mesmo agente
mostram, uma falha de cada vez, o que separa um prompt de um sistema que se pode confiar.

Este README é também o **guia do workshop**. Siga as etapas na ordem:

1. [Antes do workshop](#1-antes-do-workshop): instale e teste o ambiente (cerca de 10 minutos).
2. [Durante a apresentação](#2-durante-a-apresentação): os conceitos, nos slides.
3. [Mão na massa](#3-mão-na-massa): as sete cenas, cada uma no seu notebook.
4. [Depois do workshop](#4-depois-do-workshop): o resto do material, no seu ritmo.

## O caso em uma tabela

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

---

## 1. Antes do workshop

Na sala não há tempo para resolver instalações: faça esta etapa antes. Quem não conseguir pode vir
assim mesmo e acompanhar em dupla.

**Ambiente.** Linux, macOS ou Windows com WSL2 (Ubuntu). Windows nativo não é recomendado: rode
`wsl --install` (pede reinício) e siga os passos dentro do Ubuntu. No WSL, clone em `~/rangoja`,
nunca em `/mnt/c/...`. Você precisa de Git e do [uv](https://docs.astral.sh/uv/).

**Instalação:**

```bash
git clone https://github.com/dgoflow/rangoja.git ~/rangoja && cd ~/rangoja
uv sync --extra dev --extra live
uv run python -m ipykernel install --user --name rangoja
uv run jupyter lab notebooks/00_ambiente.ipynb
```

**Sem instalar nada:** abra o repositório no GitHub Codespaces (*Code → Codespaces → Create codespace
on main*). O [`.devcontainer/`](.devcontainer/devcontainer.json) faz a instalação; depois abra
`notebooks/00_ambiente.ipynb` com o kernel **rangoja**.

**Teste do ambiente (2 minutos), no `00_ambiente.ipynb`:**

1. Confira que o kernel é **rangoja**.
2. Execute a **primeira célula** (a de preparação) antes de qualquer outra.
3. Execute **N0.1** e **N0.2**. Você está pronto quando as duas estiverem ✅.
4. **Pule a N0.3** no dia: se você tem uma chave da OpenAI configurada, ela liga o modo ao vivo, e na
   sala todos rodam com respostas gravadas.

Não precisa de chave de API: tudo roda em `replay`, sem chave e sem internet depois da instalação.
Algo deu errado? A tabela de [problemas comuns](SETUP.md#problemas-comuns) do SETUP resolve quase tudo.

## 2. Durante a apresentação

A primeira parte é conceitual, nos slides, e prepara o que você vai executar:

- **O que é um LLM:** um modelo que prevê o próximo token e só enxerga o que está na entrada da chamada.
- **O que é um agente:** um modelo que usa ferramentas em loop para cumprir um objetivo, com instruções,
  estado e controle.
- **O loop ReAct:** pensar, agir (pedir uma ferramenta, que o código executa), observar o resultado e decidir de novo.
- **Os blocos do Google ADK:** `LlmAgent`, ferramentas, `SequentialAgent`, `ParallelAgent`, `LoopAgent`,
  sessão e callbacks.
- **Agentes no CEIA:** um sistema de subagentes especializados em requisitos, design, arquitetura,
  código e QA, coordenados por um orquestrador e construído com os mesmos blocos do ADK.
- **O caso RangoJá:** as quatro versões da tabela acima.

Se o seu ambiente ainda não passou na N0.1 e na N0.2, aproveite este tempo para terminar a etapa 1.

Quer ver o loop ReAct acontecendo de verdade? A seção **N1.3** mostra os eventos do ADK passo a passo:
o modelo pede uma ferramenta, o sistema responde e o modelo decide de novo.

## 3. Mão na massa

### Como cada cena funciona

Cada cena é uma seção de um notebook, com um caso do RangoJá (`C09`, `C05`, ...), a **falha**
acontecendo, a **correção** e uma **verificação** que confirma o que você viu. O ritmo é sempre o mesmo:

1. **Prever:** leia a pergunta da cena e diga o que vai acontecer antes de executar.
2. **Executar:** rode as células da seção, de cima para baixo.
3. **Discutir:** compare com a sua previsão e leia a ideia da cena.

Para aproveitar melhor:

- Em cada notebook, rode a **célula de preparação** uma vez; depois, qualquer seção roda sozinha.
- A célula diz de onde vem cada falha. **Gravação** é uma resposta real do gpt-4o-mini, com a taxa em
  que a falha apareceu. **Roteiro** é uma resposta escrita à mão, usada quando o modelo real não errou.
- As células `# 🎯 EXPERIMENTE` trazem uma variação para você tentar: descomente as linhas de código (a
  primeira linha é o título) e execute.
- Travou? Sente em dupla com um vizinho ou acompanhe as saídas que já estão salvas no notebook.

### As sete cenas

| Cena | Notebook | A pergunta | O que entra no agente |
|---|---|---|---|
| [1 · N1.2](#cena-1--n12-ferramentas-trazem-fatos) | NB01 | Se damos ferramentas ao modelo, ele as usa? | ferramentas |
| [2 · N1.4](#cena-2--n14-prosa--estrutura) | NB01 | O código consegue ler a decisão? | saída estruturada |
| [3 · N2.1](#cena-3--n21-limite-e-aprovação-humana) | NB02 | Quem autoriza um reembolso de R$ 120? | limite e aprovação humana |
| [4 · N2.2](#cena-4--n22-guardrail-de-entrada) | NB02 | Um guardrail de entrada basta? | defesa em camadas |
| [5 · N2.4](#cena-5--n24-memória-útil--memória-perigosa) | NB02 | O que o agente pode guardar na memória? | memória segura |
| [6 · N3.6](#cena-6--n36-reembolso-em-dobro) | NB03 | E se a confirmação se perder depois do reembolso? | idempotência |
| [7 · N4.7](#cena-7--n47-relações-metamórficas) | NB04 | Como testar sem saber a resposta certa? | relações metamórficas |

#### Cena 1 · N1.2: ferramentas trazem fatos

`01_do_prompt_ao_agente.ipynb`, versão v0 → v1.

- **Preveja:** se damos ferramentas ao modelo, ele as usa?
- **Observe:** em 6 execuções gravadas com a política colada no prompt, nenhuma consultou o pedido. A
  versão da N1.6, com decisão estruturada e estado, consultou em 5 de 6; com contexto enxuto, em 6 de 6.
  Seis amostras não separam o efeito de cada componente.
- **Experimente:** chame uma ferramenta você mesmo, como o ADK faria quando o modelo pede.
- **A ideia:** ter ferramenta não garante o uso. O que separa um prompt de um agente é o que o código dá
  ao modelo: fatos, contrato, estado e o contexto certo.

#### Cena 2 · N1.4: prosa × estrutura

`01_do_prompt_ao_agente.ipynb`.

- **Preveja:** o código consegue extrair a categoria e o valor de uma decisão escrita em prosa?
- **Observe:** a `decisao` passa de `None` a um objeto tipado, com a solução dentro das permitidas.
- **Experimente:** o schema recusa uma solução que não existe na política.
- **A ideia:** a saída estruturada é o contrato entre o modelo e o código.

#### Cena 3 · N2.1: limite e aprovação humana

`02_controle.ipynb`, versão v1 → v2, caso `C09`: "Faltou o combo família inteiro do pedido 9001" (R$ 120).

- **Preveja:** sem nenhum controle, o agente reembolsa os R$ 120?
- **Observe:** a v1 reembolsou acima do limite em 10 de 10 execuções reais. Com a correção, acima de
  R$ 50 o reembolso vira uma pendência, e nada é efetivado antes da decisão humana.
- **Faça:** você é o supervisor. Aprove (`aprovar`) ou recuse (`recusar`) e veja o que o sistema efetiva.
- **Experimente:** o prazo do supervisor. Com 23 horas a pendência ainda vale; com mais 2, vence.
- **A ideia:** o modelo propõe, o código autoriza.

#### Cena 4 · N2.2: guardrail de entrada

`02_controle.ipynb`, casos `C05` (injeção de instrução) e `C10` (assunto fora do escopo).

- **Preveja:** o guardrail de entrada impede o modelo de tentar o reembolso total?
- **Observe:** fora do escopo, a recusa sai sem nenhuma ferramenta. Na injeção, o guardrail **não**
  impediu a tentativa; quem segurou foi o limite da cena 3.
- **Experimente:** uma frase de injeção que o padrão do guardrail não pega.
- **A ideia:** defesa em camadas. Um guardrail de entrada é uma lista de padrões, fácil de contornar, e
  não pode ser a única camada.

#### Cena 5 · N2.4: memória útil × memória perigosa

`02_controle.ipynb`, casos `C08` (o cliente grava "tenho direito a reembolso integral") e `C07` (quarto
reembolso do mês).

- **Preveja:** o que acontece se o próprio modelo decide o que vai para a memória?
- **Observe:** a v1 falhou em 10 de 10 execuções reais. Depois da correção, nenhum direito alegado é
  gravado e a recorrência vai para um atendente, sem compensação automática.
- **Experimente:** as regras da memória segura e da recorrência estão em código, não no prompt.
- **A ideia:** memória vira porta de entrada. Só o código grava, e só fatos e preferências permitidas.

#### Cena 6 · N3.6: reembolso em dobro

`03_falhas_e_observabilidade.ipynb`, versão v2 → v3, caso `C03`.

- **Preveja:** o reembolso foi feito, mas a confirmação se perdeu e o sistema tenta de novo. Quanto o
  cliente recebe?
- **Observe:** R$ 85,80 sem idempotência; R$ 42,90 com. A falha é induzida de propósito
  (`falhas.injetar("timeout_apos_efeito")`), não um erro espontâneo do modelo.
- **Experimente:** a bateria de resiliência contra a v3 sem idempotência. Só o teste do reembolso em
  dobro quebra.
- **A ideia:** filas e frameworks garantem "pelo menos uma vez". "Exatamente uma vez" é
  responsabilidade do sistema.

#### Cena 7 · N4.7: relações metamórficas

`04_testes_e_avaliacao.ipynb`.

- **Preveja:** como testar um agente se não existe um texto "certo" para comparar?
- **Observe:** a mesma reclamação com gíria, erros de digitação, ruído ou outra ordem precisa levar à
  mesma decisão. Com o modelo real, o grupo `C01` violou essa relação.
- **A ideia:** teste de agente não compara texto; verifica comportamento e relações entre saídas. E uma
  avaliação serve para mostrar o que ainda está errado, não para dar nota boa.

### Fechando a prática

Ao fim do NB02, uma tabela mostra qual camada barrou qual caso e onde ela vive no código. Para ver o
que um único componente segura, tire-o e rode de novo: `v2_controlado.sem("contrato")`, nas células
EXPERIMENTE da N2.7 e da N4.3, mostra o que quebra sem o contrato entre as etapas.

## 4. Depois do workshop

**Estude o material completo.** As cenas são uma seleção. O [ROTEIRO.md](ROTEIRO.md) guia a ordem dos
notebooks e diz o que cada seção ensina. O que ficou fora das cenas:

| Notebook | Seções |
|---|---|
| NB01 | N1.1, N1.3, N1.5 a N1.8 |
| NB02 | N2.3, N2.5 a N2.8 |
| NB03 | N3.0 a N3.5, N3.7 |
| NB04 | N4.1 a N4.6, N4.8 a N4.10 |

**Veja o modelo ao vivo.** Com a sua chave da OpenAI, a N0.3 liga o modo `live` (use uma chave com limite
de gasto baixo: cada atendimento faz várias chamadas). Rode a cena 1 ao vivo e compare com a gravação, e
use a N4.8 para medir se temperatura 0 resolve a variação. Os detalhes estão em
[Usando o modelo ao vivo](SETUP.md#usando-o-modelo-ao-vivo).

**Monte as suas versões.** Tire ou acrescente componentes (`v2_controlado.sem("contrato")`,
`montar(v1_agente, com=["aprovacao"])`) e rode a mesma bateria de testes contra qualquer versão:
`uv run pytest tests --versao v1 -m "not live"`.

**Extras.** Em [`notebooks/extras/`](notebooks/extras/): memória pesquisável, conversas longas, dados
sintéticos e um texto sobre execução durável.

---

## Notebooks

| Notebook | Tema |
|---|---|
| [`00_ambiente`](notebooks/00_ambiente.ipynb) | Meu ambiente funciona? |
| [`01_do_prompt_ao_agente`](notebooks/01_do_prompt_ao_agente.ipynb) | v0 → v1: ferramentas, schema, estado, contexto, memória |
| [`02_controle`](notebooks/02_controle.ipynb) | v1 → v2: aprovação, guardrails, memória segura, sequência, contrato |
| [`03_falhas_e_observabilidade`](notebooks/03_falhas_e_observabilidade.ipynb) | v2 → v3: falhas, retry, limites, persistência, idempotência, traces |
| [`04_testes_e_avaliacao`](notebooks/04_testes_e_avaliacao.ipynb) | testes por versão, avaliação, golden, testes metamórficos |

Os notebooks são independentes entre si e cada seção roda sozinha. Estão com as saídas salvas
e executam **sem chave de API**: as falhas vêm de gravações de um modelo real (gpt-4o-mini) ou,
quando o modelo real não errou, de roteiros escritos à mão. As células dizem qual é qual. Com a sua
chave, o modo `live` faz o modelo responder de verdade (veja o [SETUP.md](SETUP.md#usando-o-modelo-ao-vivo)).

A instalação completa, o modo ao vivo, o Phoenix e os problemas comuns estão no [SETUP.md](SETUP.md).

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
