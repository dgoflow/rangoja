# Apresentação — Além do Prompt: Construindo Sistemas Agênticos Robustos

Rascunho vivo. Cada `##` é um slide; o que vem depois de **Fala:** é roteiro, não vai na tela.
Itens marcados **[decidir]** ou **[verificar]** estão em aberto.

## Premissas (não vão para os slides)

- **Formato:** hands-on. 1 hora = 50 min de apresentação + 10 min de perguntas. Cada participante executa os notebooks no próprio computador.
- **Em hands-on, o gargalo é o ambiente, não o conteúdo.** Cada participante instala sozinho; em 50 minutos não há como resolver 30 instalações diferentes ao vivo. Por isso o **pré-trabalho é parte do plano**, não opcional: sem ele, a primeira metade da palestra vira suporte.
- Ambientes recomendados: **Linux**, **WSL2 (Ubuntu)** e **macOS** (testes e notebooks verificados em macOS com Python 3.11). Windows nativo: não recomendado. Sem instalação local: o `.devcontainer/` abre o material no GitHub Codespaces ou no VS Code com Docker.
- **Na sala, todos em `replay`.** Roda sem chave e sem internet depois da instalação, e cada máquina mostra exatamente os números dos slides. Em `live` o modelo responde de verdade em **todas** as células: gasta tokens, cada atendimento fica mais lento (várias chamadas ao modelo) e a falha de uma seção pode não se repetir (a célula mostra ⚠️ em vez de ✅). Isso é ótimo para estudar em casa e ruim para uma sala que precisa ver a mesma coisa ao mesmo tempo.
- **O ao vivo fica no telão.** O apresentador, com a própria chave, mostra uma cena em `live` para a sala ver que o modelo varia. **[decidir]** qual cena; sugestão: N1.2 (a gravação diz "0 de 6 consultaram o pedido"; ao vivo, o que acontece agora?).
- **Na sala, pule a N0.3.** Ela liga o `live` sozinha quando já existe uma chave (no ambiente ou no `.env`), e muitos desenvolvedores têm uma exportada. Quem quiser rodar ao vivo usa a N0.3 em casa.
- **Quem travar não para a sala.** Fica em dupla com um vizinho, ou acompanha as saídas salvas no notebook renderizado. Dizer isso no slide 3.
- **Ritmo de cada cena:** *prever → rodar → explicar*. Antes de executar, pergunte à sala o que vai acontecer. Em `replay` a execução é rápida (os 5 notebooks juntos rodam em menos de 1 min); o que consome tempo é a conversa.
- **Células `# 🎯 EXPERIMENTE`** trazem uma variação comentada. Nas cenas da palestra que têm uma (N1.4, N2.1, N2.2, N2.4, N3.6), ela é o "faça"; o resto fica para casa. N1.2 e N4.7 não têm: o "faça" é prever e comparar.
- **Gravação × roteiro no slide.** Toda cena diz de onde vem a falha. N3.6 é **roteiro** com falha induzida (o timeout é provocado de propósito); a matriz da N4.7 roda com modelo roteirizado, e o número da cena (a violação no grupo `C01`) vem das gravações da v3; as demais cenas vêm de gravações do gpt-4o-mini. Os números são desse modelo: se perguntarem "e com um modelo mais forte?", a resposta honesta é que não medimos, e que o material permite medir (`RANGOJA_MODELO` + modo `record`).
- **Ao vivo, pular a N0.4 (Phoenix) e a N0.6 (suíte de testes).** A primeira sobe um servidor e pode colidir com a porta 6006 em algumas máquinas; a segunda roda o pytest. Nenhuma é necessária para a palestra.
- **Apoio:** **[decidir]** quem ajuda com ambiente durante a palestra (monitor, colega, canal de chat).
- **[verificar]** Instalação completa e NB00 em WSL2 limpo, e no Codespaces pelo `.devcontainer/`.
- **[verificar]** Ensaiar com cronômetro, de preferência com alguém executando junto.

## Linha do tempo (50 min)

| Minuto | Cena | Duração |
|---|---|---|
| 0:00 | Abertura + smoke test (N0.1, N0.2) | 5 |
| 0:05 | N1.2 — ferramentas trazem fatos | 6 |
| 0:11 | N1.4 — prosa × estrutura | 4 |
| 0:15 | N2.1 — limite e aprovação humana | 7 |
| 0:22 | N2.2 — guardrail de entrada (defesa em camadas) | 5 |
| 0:27 | N2.4 — memória útil × memória perigosa | 5 |
| 0:32 | N3.6 — reembolso em dobro (idempotência) | 7 |
| 0:39 | N4.7 — relações metamórficas | 6 |
| 0:45 | Encerramento | 5 |
| 0:50 | Perguntas | 10 |

**Folgas, na ordem de corte se atrasar:** N1.4 (4 min), N2.4 (5 min). Isso devolve 9 minutos.
**Fora da palestra, para casa:** N1.3, N1.5–N1.7, N2.3, N2.5–N2.7, N3.1–N3.5, N4.1–N4.6, N4.8–N4.9 e os extras.

---

## Pré-trabalho (enviar antes do evento)

Mensagem curta, com a promessa e uma tarefa:

> Na palestra você vai executar os notebooks. Leva 10 minutos instalar antes; durante a palestra não dá tempo. Siga o passo a passo, abra o `00_ambiente.ipynb` e confira que N0.1 e N0.2 estão ✅. Quem não conseguir, venha assim mesmo: dá para acompanhar em dupla.

- Não é preciso chave da OpenAI: na sala tudo roda em `replay`. Quem quiser repetir em casa com o modelo ao vivo usa uma chave com limite de gasto baixo, pela N0.3.
- Sem como instalar? Abra o repositório no GitHub Codespaces (botão *Code → Codespaces*): o `.devcontainer/` instala tudo.
- Windows: `wsl --install` (pede reinício), depois os comandos do slide 2 dentro do Ubuntu.
- **[decidir]** Canal para tirar dúvidas de instalação antes do dia.

---

## Parte 1 — Abertura e smoke test (5 min)

### Slide 1 — Hoje você executa

- QR code + URL curta do repositório
- Cada cena: **preveja → execute → discuta**
- Instalou antes? Abra o `00_ambiente.ipynb`

**Fala:** O objetivo não é decorar, é ver cada falha acontecer na sua máquina.

### Slide 2 — O que precisa (e o que não)

| Ambiente | Situação |
|---|---|
| Linux | recomendado |
| Windows com WSL2 (Ubuntu) | recomendado |
| macOS | recomendado |
| Windows nativo (PowerShell) | não recomendado |

Sem chave, tudo roda em `replay`, e é assim que vamos rodar hoje. O modo `live` (a sua chave, na N0.3) fica para casa.

```bash
git clone https://github.com/dgoflow/rangoja.git ~/rangoja && cd ~/rangoja
uv sync --extra dev --extra live
uv run python -m ipykernel install --user --name rangoja
uv run jupyter lab notebooks/00_ambiente.ipynb
```

> No WSL, clone em `~/rangoja`, **nunca** em `/mnt/c/...`.

**Fala:** Replay quer dizer respostas gravadas de um modelo real; onde o modelo real não errou, a falha é um roteiro escrito à mão, e a célula diz qual é qual.
**[verificar]** URL HTTPS assume repositório público.

### Slide 3 — Smoke test: 2 minutos

1. Confira que o kernel é **rangoja** (os notebooks já abrem com ele)
2. Execute a **primeira célula** (a de preparação) antes de qualquer outra
3. Execute **N0.1** e **N0.2**. Pronto quando os dois estiverem ✅
4. **Pule a N0.3** (se você tem uma chave da OpenAI configurada, ela liga o modo ao vivo)

> Sem a primeira célula aparece `NameError: name '...' is not defined`.
> Editou o `.env` com o notebook aberto? Reinicie o kernel e rode a primeira célula de novo (ou use a N0.3).

**Não rodou em 2 minutos? Sem problema.** Sente com um vizinho ou acompanhe as saídas salvas. Resolvemos depois.

**Fala (olhando o N0.2):** o agente só com prompt respondeu. Preveja: ele consultou o pedido?

---

## Parte 2 — Cenas hands-on (40 min)

Em cada cena: o slide mostra o caso e a pergunta; a plateia prevê; todos executam; o apresentador fecha com a ideia.

### N1.2 — Ferramentas trazem fatos (6 min)

- **Pergunta:** se damos ferramentas ao modelo, ele as usa?
- **Número:** em 6 execuções gravadas com a política colada, 0 consultaram o pedido.
- **Ponte:** com decisão estruturada e estado, a versão da N1.6 consultou em 5 de 6; com contexto enxuto, em 6 de 6. Seis amostras não separam o efeito de cada componente: diga isso.
- **No telão (sugestão):** rode esta cena em `live` e compare com a gravação.
- **Ideia:** ter ferramenta não garante o uso; o que separa um prompt de um agente é o que o código dá ao modelo.

### N1.4 — Prosa × estrutura (4 min) *[folga]*

- **Pergunta:** o código consegue ler a decisão?
- **Imagem:** `decisao` passa de `None` a objeto tipado.
- **Ideia:** a saída estruturada é o contrato com o código.

### N2.1 — Limite e aprovação humana (7 min)

- **Caso `C09`:** "Faltou o combo família inteiro do pedido 9001" (R$ 120).
- **Número:** a v1 reembolsou acima do limite em 10 de 10 execuções reais.
- **Faça:** você é o supervisor. Aprove (`aprovar`) ou recuse (`recusar`) e veja o que o sistema efetiva.
- **Ideia:** o modelo propõe, o código autoriza.

### N2.2 — Guardrail de entrada (5 min)

- **Casos:** `C05` (injeção de instrução) e `C10` (fora do escopo).
- **Ponto central:** na gravação, o guardrail **não impediu** o modelo de tentar; quem segurou foi o limite da N2.1.
- **Faça:** a célula EXPERIMENTE mostra uma frase de injeção que o padrão do guardrail não pega.
- **Ideia:** defesa em camadas: o guardrail de entrada é uma lista de padrões, fácil de contornar, e não pode ser a única camada.

### N2.4 — Memória útil × memória perigosa (5 min) *[folga]*

- **Casos:** `C08` (cliente grava "tenho direito a reembolso integral") e `C07` (quarto reembolso do mês).
- **Número:** falhas reais em 10 de 10 execuções (v1).
- **Ideia:** memória vira porta de entrada; só o código grava, e só fatos e preferências permitidas.

### N3.6 — Reembolso em dobro (7 min)

- **Caso `C03`:** a confirmação se perde depois do efeito.
- **Origem:** roteiro com falha induzida (`falhas.injetar("timeout_apos_efeito")`), não um erro espontâneo do modelo. Dizer no slide.
- **Número:** R$ 85,80 sem idempotência, R$ 42,90 com.
- **Faça:** compare os dois totais lado a lado.
- **Ideia:** filas e frameworks garantem "pelo menos uma vez"; "exatamente uma vez" é responsabilidade do sistema.

### N4.7 — Relações metamórficas (6 min)

- **Pergunta:** como testar sem saber a resposta certa?
- **Número:** com o modelo real, o grupo `C01` violou a invariância.
- **Ideia:** teste de agente não compara texto; verifica comportamento e relações entre saídas.

---

## Parte 3 — Encerramento (5 min)

- Tabela de recapitulação: qual camada barrou qual caso (final do NB02)
- A avaliação serve para mostrar o que ainda está errado, não para dar nota boa
- **Para levar, uma linha:** `v2_controlado.sem("contrato")` e veja o que quebra (células EXPERIMENTE da N2.7 e da N4.3)
- O que ficou de fora está no repositório: `ROTEIRO.md` guia a ordem dos notebooks
- Em casa, com a sua chave: N0.3 liga o `live` e a N4.8 mede se temperatura 0 resolve
- Links: repositório, [`ROTEIRO.md`](../ROTEIRO.md), [`IMPLEMENTACAO.md`](../IMPLEMENTACAO.md)

## Perguntas (10 min)

- **[decidir]** Dúvidas de ambiente ficam para depois, para não consumir esse tempo.
