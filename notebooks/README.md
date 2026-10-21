# Notebooks do workshop — especificação

> Status: NB00–NB04 implementados e executados em `replay` (a especificação está em `specs/`;
> `extras/` x1–x3 implementados, x5 é texto). Decisões e verificação no ADK: [specs/decisoes.md](specs/decisoes.md).

Workshop **Além do Prompt: Construindo Sistemas Agênticos Robustos** (AI Brasil
Experience 2026). Os notebooks são o **material completo**: cobrem todo o conteúdo e
podem ser estudados sem a apresentação. A apresentação de 45 minutos é uma seleção feita
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
7. **Toda correção tem verificação.** Cada seção termina com `verificar(...)`, uma
   asserção explícita. Serve ao participante, ao ensaio e ao CI (`nbmake`).

## Componentes e versões

| Versão | Componentes | Introduzidos em |
|---|---|---|
| `v0` | `prompt` (agente sem ferramentas, política colada na instrução) | N1.1 |
| `v1` | `ferramentas`, `schema`, `estado`, `contexto_enxuto`, `memoria_livre` | N1.2–N1.7 |
| `v2` | `v1` − `memoria_livre` + `aprovacao`, `guardrail_entrada`, `guardrail_saida`, `memoria_segura`, `sequencia`, `categorias`, `contrato` | N2.1–N2.7 |
| `v3` | `v2` + `erros_estruturados`, `retry`, `fallback`, `limites`, `persistencia`, `idempotencia` | N3.2–N3.6 |

Dependências: `contexto_enxuto` substitui `prompt` (a política deixa de ser colada e passa a ser consultada); `categorias` e `contrato` exigem `sequencia`; `memoria_segura` substitui
`memoria_livre`; `persistencia` liga a retomada (`App` retomável). `montar` resolve as
dependências e avisa o que desligou junto.

Cada versão é também um pacote de agente (`rangoja/versoes/v1/agent.py` com
`root_agent`), para `adk web` e `adk eval`.

## Padrão de seção (NB01–NB03)

| Bloco | Conteúdo | Tipo de célula |
|---|---|---|
| **Cenário** | O caso (`Cxx`) e o que se espera do sistema | markdown |
| **Falha** | `atender(s.falha, s.caso, gravacao=...)` ou `roteiro=...`; mostra o erro; `verificar_falha(...)` | código + markdown curto |
| **Conceito** | A ideia em 3–6 linhas; `mostrar(modulo)` exibe o componente | markdown + código |
| **Correção** | `atender(s.correcao, s.caso)` | código |
| **Verificação** | `verificar(...)` | código |
| **Experimente** (opcional) | Uma variação para o participante tentar | código comentado |

O NB04 usa "Pergunta → Técnica → Resultado em v0…v3" (ver a spec).

Identificadores de seção (`N1.2`, `N3.4`…) são estáveis e são referenciados pelos slides
e pelo registro `rangoja/secoes.py`.

## Contrato com o pacote `rangoja`

Os notebooks dependem **só** desta superfície. O resto do pacote é livre.

```python
from rangoja.notebook import preparar_ambiente, preparar_secao, mostrar, verificar, verificar_falha, matriz
from rangoja.casos import caso                    # caso("C04") -> Caso
from rangoja.versoes import v0, v1, v2, v3, montar
from rangoja.execucao import atender, continuar, aprovar, recusar, expirar_pendencias, reiniciar_runner
from rangoja.trajetoria import chamou, ferramenta_antes, contar_chamadas, publicas
from rangoja.politica import solucoes_permitidas, categoria_principal
from rangoja import falhas, relogio
```

| Nome | Assinatura / comportamento |
|---|---|
| `preparar_ambiente()` | Carrega `.env`, define o modo, liga o Phoenix se disponível, imprime o resumo. Idempotente |
| `preparar_secao(id) -> Secao` | Isola e semeia a seção; devolve `Secao` com `id`, `caso`, `falha` (versão), `correcao` (versão), `gravacoes` (dict nome → id), `roteiros` |
| `mostrar(obj)` | Exibe o código-fonte de um componente, função ou ferramenta, com destaque |
| `verificar(condicao, mensagem)` | Asserção com saída legível (✅/❌) |
| `verificar_falha(atendimento, condicao, mensagem)` | Para células de falha: só afirma se a resposta veio de gravação ou roteiro; em `live`, vira aviso (⚠️) |
| `matriz(arquivo_de_teste, versoes) -> Tabela` | Roda o pytest por versão em subprocesso; células **passa / falha / não se aplica** |
| `caso(id) -> Caso` | `id`, `mensagens` (turnos), `pedido_id`, `cliente_id`, `esperado`, `origem`, `transformacao` |
| `montar(base, com=[], sem=[]) -> Versao` | Variante de versão; `Versao.sem(*nomes)` e `Versao.com(*nomes)` são atalhos |
| `atender(versao, caso, *, gravacao=None, roteiro=None, cliente_id=None, temperatura=None, run_config=None) -> Atendimento` | Roda todos os atendimentos e turnos do caso; nunca lança: erro vira `status="erro"` |
| `continuar(atendimento, mensagem) -> Atendimento` | Mais um turno na mesma sessão |
| `aprovar(atendimento)` / `recusar(atendimento, motivo)` | Responde à confirmação pendente e retoma |
| `expirar_pendencias()` | Recusa, com motivo "prazo vencido", toda pendência além do prazo segundo `relogio` |
| `reiniciar_runner()` | Descarta o runner e os objetos em memória, como se o processo tivesse caído |
| `chamou(atendimento, ferramenta)`, `ferramenta_antes(atendimento, a, b)`, `contar_chamadas(atendimento, ferramenta)`, `publicas(trajetoria)` | Funções de trajetória; ignoram ferramentas internas do ADK (`set_model_response`, `adk_request_confirmation`, `transfer_to_agent`) |
| `solucoes_permitidas(categoria)`, `categoria_principal(problemas)` | Regras da política, em código |
| `falhas.injetar(tipo, **opcoes)` | Gerenciador de contexto (`with`); tipos em [03](specs/03_falhas_e_observabilidade.md) |
| `relogio.avancar(horas=...)` | Relógio controlável para prazos |

**`Atendimento`:** `sessao_id`, `invocation_id`, `versao` (composição), `caso_id`,
`status` (`concluido`, `aguardando_cliente`, `aguardando_aprovacao`, `escalado`,
`encaminhado_seguranca`, `erro`), `decisao` (`Decisao` ou `None` na v0), `resposta`
(texto ao cliente), `turnos` (lista com mensagem, resposta e decisão de cada turno),
`trajetoria` (chamadas de ferramenta em ordem, com argumentos e resultados), `estado`
(estado final da sessão), `eventos` (eventos brutos do ADK), `fonte` (`cache`,
`gravacao`, `roteiro`, `live`), `trace_url`, `anteriores` (atendimentos anteriores do mesmo
caso, ex.: `C08`, `C13`), `erro`, `pendencia`, `modelos_usados`.

**`Decisao`** (schema da resolução): `categoria`, `problemas` (lista), `solucao`,
`valor`, `pedido_id`, `justificativa`, `sinais_de_risco`, `mensagem_ao_cliente` (preenchida
pelo agente único; nula na sequência, em que o agente de resposta escreve o texto).

## Estrutura do repositório

Especificada em [`specs/pacote/README.md`](../specs/pacote/README.md). Pontos que os
notebooks enxergam: `rangoja/versoes/vN/agent.py` (pacotes de agente), `rangoja/gravacoes/`
(gravações por seção), `rangoja/roteiros/` (roteiros por seção), `tests/`, `evals/` e
`.cache/modelo/` (versionado).

## Modos de execução

| `RANGOJA_MODO` | Comportamento |
|---|---|
| `replay` (padrão) | Respostas vêm do cache, das gravações e dos roteiros. Sem chave de API, sem rede. |
| `live` | Chama o modelo quando não há cache. Gravações nomeadas continuam valendo nas células de falha, salvo `gravacao=None`. |
| `record` | Chama o modelo e regrava cache e gravações. Uso dos autores. |

Em `replay`, todo notebook roda do início ao fim sem chave e gera traces no Phoenix
(o span do modelo é marcado com a fonte da resposta). Células que precisam de modelo
real são marcadas `# requer: live` e, em `replay`, exibem o resultado gravado.

**Pilha do modelo** (abaixo dos callbacks, então guardrails sempre rodam), de fora para
dentro: `fallback → retry → injeção de falhas → fonte (cache | gravação | roteiro | Gemini)`.

## Convenções

- Idioma: português nos textos, no domínio (`pedido`, `reembolso`) e nos identificadores
  do pacote; APIs do ADK mantêm os nomes originais.
- Uma ideia por célula de markdown; no máximo ~8 linhas.
- Nenhuma célula longa de código no notebook: lógica no pacote; o notebook chama e mostra.
- Saídas executadas ficam salvas no `.ipynb` (renderizam no GitHub; servem de rede de
  proteção na demo).
- Células "Experimente" começam com `# 🎯 EXPERIMENTE`.
- Dependências fixadas no `uv.lock`: `google-adk==1.33.0`, `arize-phoenix`,
  `openinference-instrumentation-google-adk`, `pydantic`, `pyyaml`, `pytest`, `nbmake`,
  `jupyter`.

## Ordem de implementação

Ver [`specs/pacote/README.md`](../specs/pacote/README.md#ordem-de-implementação). Os
notebooks são escritos depois do pacote, dos testes determinísticos e da rodada
exploratória de gravação.
