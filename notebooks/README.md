# Notebooks do workshop — especificação

> Status: NB00–NB04 implementados e executados em `replay` (a especificação está em `specs/`;
> `extras/` x1–x3 implementados, x5 é texto). Decisões e verificação no ADK: [specs/decisoes.md](specs/decisoes.md).

Workshop **Além do Prompt: Construindo Sistemas Agênticos Robustos** (AI Brasil
Experience 2026). Os notebooks são o **material completo**: cobrem todo o conteúdo e
podem ser estudados sem a apresentação. A apresentação (50 minutos e 10 de perguntas, em [`palestra/`](../palestra/apresentacao.md)) é uma seleção feita
a partir deles.

## Mapa

| Notebook | Pergunta que responde | Versões | Spec |
|---|---|---|---|
| `00_ambiente.ipynb` | Meu ambiente funciona? | v1 | [specs/00_ambiente.md](specs/00_ambiente.md) |
| `01_do_prompt_ao_agente.ipynb` | O que separa um prompt de um agente? | v0 → v1 | [specs/01_do_prompt_ao_agente.md](specs/01_do_prompt_ao_agente.md) |
| `02_controle.ipynb` | Como impedir que o agente faça o que não deve? | v1 → v2 | [specs/02_controle.md](specs/02_controle.md) |
| `03_falhas_e_observabilidade.ipynb` | O que acontece quando algo dá errado, e como eu vejo? | v2 → v3 | [specs/03_falhas_e_observabilidade.md](specs/03_falhas_e_observabilidade.md) |
| `04_testes_e_avaliacao.ipynb` | Como provar que funciona sem saber a resposta certa? | v0…v3 sob teste | [specs/04_testes_e_avaliacao.md](specs/04_testes_e_avaliacao.md) |
| `extras/` | Temas opcionais | — | [specs/extras.md](specs/extras.md) |

Casos, política e dados: [specs/casos.md](specs/casos.md).

Arco: **funciona → se comporta → aguenta falhas e se deixa ver → prova que funciona.**

## Princípios de desacoplamento

Qualquer notebook, e qualquer seção dentro dele, pode ser aberto, executado e ensinado
sozinho. Isso serve ao estudo individual e à apresentação, que escolhe seções.

1. **Notebooks não dependem uns dos outros.** Nenhum notebook lê arquivos gerados por
   outro. O que um notebook precisa de outro vem do **pacote** (versões, casos,
   gravações), nunca de uma execução anterior.
2. **Seções independentes.** Cada seção abre com `s = preparar_secao("N2.3")`, que cria
   armazenamentos novos, semeia o estado inicial declarado para a seção e desliga falhas
   injetadas. O apresentador pode pular de N2.1 para N2.5 sem rodar o meio.
3. **Versões montáveis, conceitos isolados.** Cada conceito vive em um módulo pequeno do
   pacote e é um **componente** com nome. Uma versão é uma montagem de componentes. O
   notebook mostra o módulo do conceito (curto, legível) e roda a montagem que o inclui.
   Variantes se escrevem `v2.sem("contrato")` ou `montar(v1, com=["aprovacao"])`.
4. **Correções cumulativas.** Dentro de um notebook, a correção da seção *k* é a da
   seção *k−1* mais um componente. A última seção de cada notebook roda exatamente a
   versão de chegada.
5. **Casos canônicos compartilhados.** Toda demonstração usa um caso com identificador
   (`C04` = golpe). Os mesmos casos alimentam os testes do NB04.
6. **Falhas reproduzíveis e honestas.** Toda falha demonstrada usa uma **gravação**
   (resposta real do modelo, guardada) ou um **roteiro** (resposta escrita à mão: falha
   induzida). A célula diz qual é. Nunca apresentar falha induzida como espontânea.
7. **Toda correção tem verificação.** Cada seção termina com `afirmar(...)` ou `esperar(...)`, uma
   asserção explícita. Serve ao participante, ao ensaio e ao CI (`nbmake`).

## Componentes e versões

| Versão | Componentes | Introduzidos em |
|---|---|---|
| `v0` | `prompt` (agente sem ferramentas, política colada na instrução) | N1.1 |
| `v1` | `ferramentas`, `schema`, `estado`, `contexto_enxuto`, `memoria_livre` | N1.2–N1.7 |
| `v2` | `v1` − `memoria_livre` + `aprovacao`, `guardrail_entrada`, `guardrail_saida`, `memoria_segura`, `sequencia`, `categorias`, `contrato` | N2.1–N2.7 |
| `v3` | `v2` + `erros_estruturados`, `retry`, `fallback`, `limites`, `persistencia`, `idempotencia` | N3.2–N3.6 |

Dependências: `contexto_enxuto` substitui `prompt` (a política deixa de ser colada e passa a ser consultada); `categorias` e `contrato` exigem `sequencia`; `memoria_segura` substitui
`memoria_livre`; `persistencia` guarda as sessões em SQLite (`SqliteSessionService`). `montar` resolve as
dependências e avisa o que desligou junto.

Cada versão tem um nome que diz o que ela é: `v0_so_prompt`, `v1_agente`, `v2_controlado` e
`v3_robusto` (os mesmos objetos que `v0`…`v3`). As versões não são pacotes de agente para `adk web`
ou `adk eval`: os notebooks rodam o `Runner` do ADK como biblioteca.

## Padrão de seção (NB01–NB03)

| Bloco | Conteúdo | Tipo de célula |
|---|---|---|
| **Cenário** | O caso (`Cxx`) e o que se espera do sistema | markdown |
| **Falha** | `atender_caso(s.caso, com=s.falha, replay=...)` ou `roteiro=...`; mostra o erro; `esperar(...)` | código + markdown curto |
| **Conceito** | A ideia em 3–6 linhas; `comparar(s.falha, s.correcao)` mostra o que muda; `mostrar(modulo)` exibe o componente | markdown + código |
| **Correção** | `atender_caso(s.caso, com=s.correcao, ...)` | código |
| **Verificação** | `afirmar(...)` para o que o código garante; `esperar(...)` para o que depende do modelo | código |
| **Experimente** | Uma variação para o participante tentar | código comentado |

O NB01 monta as versões à vista (`v0_so_prompt.com("ferramentas")`) em vez de usar `preparar_secao`, porque
é ali que a ideia de versão como conjunto de componentes é apresentada.

O NB04 usa "Pergunta → Técnica → Resultado em v0…v3" (ver a spec).

Identificadores de seção (`N1.2`, `N3.4`…) são estáveis e são referenciados pelos slides
e pelo registro `rangoja/secoes.py`.

## Contrato com o pacote `rangoja`

Os notebooks dependem **só** desta superfície. O resto do pacote é livre.

```python
from rangoja.notebook import (preparar_ambiente, preparar_secao, mostrar, comparar, afirmar, esperar,
                              resumo, amostra, matriz)
from rangoja.casos import caso                    # caso("C04") -> Caso
from rangoja.versoes import v0_so_prompt, v1_agente, v2_controlado, v3_robusto, montar   # e v0…v3
from rangoja.execucao import (atender_caso, atender, continuar, aprovar, recusar, expirar_pendencias,
                              reiniciar_runner, estado_persistido)
from rangoja.trajetoria import chamou, ferramenta_antes, contar_chamadas
from rangoja.politica import solucoes_permitidas, categoria_principal
from rangoja import falhas, relogio
```

| Nome | Assinatura / comportamento |
|---|---|
| `preparar_ambiente()` | Carrega `.env`, define o modo, liga o Phoenix (salvo `RANGOJA_PHOENIX=off`), imprime o resumo. Idempotente |
| `preparar_secao(id) -> Secao` | Isola a seção (armazém novo, relógio e falhas zerados); devolve `Secao` com `id`, `caso`, `falha` (versão), `correcao` (versão), `gravacoes` (dict rótulo → gravação), `casos_extra` e `roteiro(versao)` (o roteiro da seção na forma da versão) |
| `mostrar(obj)` | Exibe o código-fonte de um componente, função ou ferramenta, com destaque |
| `comparar(antes, depois)` | O que muda entre duas versões, lido dos agentes construídos: componentes, prompt, ferramentas, callbacks, execução. Com `antes=None`, a ficha completa |
| `afirmar(condicao, mensagem)` | Asserção com saída legível (✅/❌); interrompe o notebook se falhar. Nome antigo: `verificar` |
| `esperar(atendimento, condicao, mensagem)` | Para o que depende do modelo: só afirma se a resposta veio de gravação ou roteiro; em `live`, ✅ ou aviso (⚠️). Nomes antigos: `verificar_falha`, `conferir` |
| `matriz(arquivo_de_teste, versoes) -> Tabela` | Roda o pytest por versão em subprocesso; células **passa / falha / não se aplica** |
| `caso(id) -> Caso` | `id`, `cliente_id`, `pedido_id`, `atendimentos` (mensagens de cada atendimento), `esperado`, `origem`, `transformacao`, `relacao` |
| `montar(base, com=[], sem=[]) -> Versao` | Variante de versão; `Versao.sem(*nomes)` e `Versao.com(*nomes)` são atalhos |
| `atender_caso(caso, com, replay=None, *, roteiro=None, cliente_id=None, temperatura=None) -> Atendimento` | Roda todos os atendimentos e turnos do caso; nunca lança: erro vira `status="erro"`. `replay` é a gravação usada só em modo `replay`; `roteiro` vale em qualquer modo |
| `atender(versao, caso, *, gravacao=None, roteiro=None, cliente_id=None, temperatura=None)` | O mesmo, com a ordem antiga dos argumentos (usado pelos testes e scripts) |
| `continuar(atendimento, mensagem) -> Atendimento` | Mais um turno na mesma sessão |
| `aprovar(atendimento)` / `recusar(atendimento, motivo)` | Resolve a pendência do atendimento na fila do armazém: aprovar efetiva o reembolso (idempotente); recusar encerra e abre um ticket |
| `expirar_pendencias()` | Encerra como "expirada" (prazo vencido) toda pendência aberta além de 24 h segundo `relogio`, e abre um ticket; devolve as encerradas |
| `reiniciar_runner(atendimento)` | Descarta o runner e o serviço de sessões do atendimento, como se o processo tivesse caído |
| `estado_persistido(atendimento)` | O estado da sessão lido do SQLite, ou `None` sem `persistencia` |
| `chamou(trajetoria, ferramenta)`, `ferramenta_antes(trajetoria, a, b)`, `contar_chamadas(trajetoria, ferramenta)` | Funções sobre `atendimento.trajetoria`, que já vem sem as ferramentas internas do ADK (`set_model_response`, `adk_request_confirmation`, `transfer_to_agent`) |
| `solucoes_permitidas(categoria)`, `categoria_principal(problemas)` | Regras da política, em código |
| `falhas.injetar(tipo, **opcoes)` | Gerenciador de contexto (`with`); tipos em [03](specs/03_falhas_e_observabilidade.md) |
| `relogio.avancar(hours=...)` | Relógio controlável para prazos (argumentos de `timedelta`) |

**`Atendimento`:** `sessao_id`, `versao` (nome da composição), `caso_id`, `cliente_id`,
`status` (`concluido`, `aguardando_cliente`, `aguardando_aprovacao`, `escalado`,
`encaminhado_seguranca`, `erro`), `decisao` (`Decisao` ou `None` na v0), `resposta`
(texto ao cliente), `turnos` (lista com a mensagem e a resposta de cada turno),
`trajetoria` (chamadas de ferramenta em ordem, com argumentos e resultados), `estado`
(estado final da sessão), `eventos` (eventos brutos do ADK), `fonte` (`cache`,
`gravacao`, `roteiro`, `live`), `trace_url`, `anteriores` (atendimentos anteriores do mesmo
caso, ex.: `C08`, `C13`), `erro`, `pendencia`, `modelos_usados`, `tentativas`.

**`Decisao`** (schema da resolução): `categoria`, `problemas` (lista), `solucao`,
`valor`, `pedido_id`, `justificativa`, `sinais_de_risco`, `mensagem_ao_cliente` (preenchida
pelo agente único; nula na sequência, em que o agente de resposta escreve o texto).

## Estrutura do repositório

Especificada em [`specs/pacote/README.md`](../specs/pacote/README.md). Pontos que os
notebooks enxergam: `rangoja/gravacoes/` (gravações por seção), `rangoja/roteiros.py` (roteiros por
seção), `tests/` e `evals/`. O cache do modelo (`.cache/`) **não** é versionado: nada em `replay` depende dele.

## Modos de execução

| `RANGOJA_MODO` | Comportamento |
|---|---|
| `replay` (padrão) | Respostas vêm dos roteiros, das gravações e do cache. Sem chave de API, sem rede. |
| `live` | O modelo de `RANGOJA_MODELO` responde de verdade: a gravação passada em `replay=` é ignorada (vira referência em `amostra`) e o cache não é lido. Os roteiros continuam valendo. |
| `record` | Como `live`, e as respostas novas são salvas no cache (`.cache/`). As gravações nomeadas de `rangoja/gravacoes/` são feitas pelos scripts `gravar_secoes.py` e `rodada_exploratoria.py`. Uso dos autores. |

Em `replay`, todo notebook roda do início ao fim sem chave e gera traces no Phoenix
(o span do modelo é marcado com a fonte da resposta). O que só faz sentido com o modelo
real fica numa célula `# 🎯 EXPERIMENTE` comentada e marcada `# requer: live` (ex.: N4.8).

**Pilha do modelo** (abaixo dos callbacks, então guardrails sempre rodam), de fora para
dentro: `fallback → retry → injeção de falhas → fonte (cache | gravação | roteiro | modelo ao vivo)`.

## Convenções

- Idioma: português nos textos, no domínio (`pedido`, `reembolso`) e nos identificadores
  do pacote; APIs do ADK mantêm os nomes originais.
- Uma ideia por célula de markdown; no máximo ~8 linhas.
- Nenhuma célula longa de código no notebook: lógica no pacote; o notebook chama e mostra.
- Saídas executadas ficam salvas no `.ipynb` (renderizam no GitHub; servem de rede de
  proteção na demo).
- Células "Experimente" começam com `# 🎯 EXPERIMENTE` e ficam comentadas: o notebook roda inteiro sem elas.
- **Os `.ipynb` são gerados** por `scripts/gerar_nb*.py` e `scripts/gerar_extras.py`. Edite o gerador,
  rode-o e execute o notebook com `uv run python scripts/executar_notebooks.py <notebook>`; uma edição
  feita direto no `.ipynb` se perde na próxima geração.
- Dependências fixadas no `uv.lock` (`uv sync --locked`): `google-adk==1.33.0`, `litellm==1.82.6`,
  `arize-phoenix`, `openinference-instrumentation-google-adk`, `pydantic`, `pyyaml`, `pytest`, `nbmake`,
  `jupyterlab`.

## Ordem de implementação

Ver [`specs/pacote/README.md`](../specs/pacote/README.md#ordem-de-implementação-histórico). Os
notebooks são escritos depois do pacote, dos testes determinísticos e da rodada
exploratória de gravação.
