# NB04 — Testes e avaliação (`04_testes_e_avaliacao.ipynb`)

> Especificação original do notebook, mantida como registro. O notebook em si e o
> [`notebooks/README.md`](../README.md) descrevem o que existe hoje; os desvios estão em
> [`IMPLEMENTACAO.md`](../../IMPLEMENTACAO.md#desvios-da-spec-e-por-quê).

**Pergunta:** como provar que funciona sem saber a resposta certa?
**Sob teste:** `v0`, `v1`, `v2`, `v3` e variantes. Recurso pedagógico central: **a
mesma bateria contra todas as versões**, com os testes ficando verdes à medida que o
sistema amadurece.

**Ideia central:** não há oráculo para "a resposta certa"; cada técnica responde a uma
pergunta diferente, e juntas verificam **comportamento**, **uso de ferramentas** e
**qualidade das respostas** (as três coisas que a proposta do workshop promete).

**Ao final, o participante sabe:**
- por que métricas genéricas não servem e como definir critérios do domínio;
- separar teste de orquestração (modelo roteirizado) de teste de decisão (modelo real);
- testar resiliência com falhas injetadas;
- escrever asserções sobre trajetória e medir estabilidade;
- usar avaliadores programáticos e um juiz validado;
- escrever relações metamórficas;
- colocar tudo no CI.

**Arquivos mostrados:** `tests/conftest.py` (opção `--versao`), `tests/test_orquestracao.py`,
`tests/test_resiliencia.py`, `tests/test_trajetoria.py`, `tests/test_qualidade.py`,
`tests/test_metamorficos.py`, `evals/golden.yaml`, `evals/trajetoria.evalset.json`,
`evals/test_config.json`, `evals/rotulos_tom.yaml`, `.github/workflows/ci.yml`.

**Padrão de seção:** Pergunta → Técnica (mostrar o teste) → Resultado com
`matriz(arquivo, [v0, v1, v2, v3])`: **passa**, **falha** ou **não se aplica** (ex.:
trajetória na v0, que não tem ferramentas).

## Orçamento do modo `live`

| Seção | Execuções | Observação |
|---|---|---|
| N4.5 | 13 casos × 4 versões × 5 repetições = 260 atendimentos | `v0` não se aplica na trajetória; na prática ~195 |
| N4.6 | 13 casos × 4 versões + 30 respostas no juiz | — |
| N4.7 | 7 variantes + 2 origens × 4 versões × 5 repetições = 180 | — |
| N4.8 | 2 casos × 10 repetições | — |

O modo `live` do NB04 é para os autores (gravação). O participante vê as gravações; as
células `# requer: live` mostram quanto custaria rodar.

## Seções

### N4.1 — O problema do oráculo
- Três respostas válidas para `C01` e uma inválida que "parece" melhor (gravações).
- **Contraexemplo (gravação ou roteiro):** um juiz genérico de "utilidade" dá nota alta à
  resposta que viola a política.
- **Conceito:** testar comportamento esperado e relações entre saídas, não um texto exato.

### N4.2 — Critérios do domínio e golden dataset
- **Critérios:** decisão conforme a política; nada irreversível sem autorização; golpe
  sempre encaminhado; nenhuma PII do entregador; nenhum direito gravado na memória; tom
  adequado ao cliente.
- **Golden dataset** (`evals/golden.yaml`): `C01`–`C13` com o comportamento esperado do
  `casos.yaml` (categoria, soluções permitidas, ferramentas obrigatórias/proibidas, ordem,
  status), incluindo os adversariais do NB02 (`C04`, `C05`, `C08`, `C10`, `C12`).
- **De onde vêm os critérios:** análise de erros (rotular falhas em traces reais e
  agrupá-las em categorias). Foi assim que se chegou às 3 falhas do PDC.
- **Mencionar:** como ampliar o dataset (extra `x3`).

### N4.3 — Orquestração: modelo roteirizado
- **Pergunta:** dado que o modelo decidiu X, o sistema faz a coisa certa?
- **Técnica:** a fonte de respostas é um **roteiro** (respostas fixas); callbacks,
  ferramentas e orquestração rodam de verdade. Testes: decisão de R$ 120 vira pendência;
  golpe nunca alcança `registrar_reembolso`; sem `pedido_id` não há decisão; PII
  roteirizada não sai; memória não grava direitos; injeção não chega à ferramenta.
- **Resultado:** matriz `v0…v3` (v1 falha; v2 e v3 passam; v0 "não se aplica" nos testes que exigem ferramentas). Rápido, barato,
  determinístico: roda em todo push.
- **Limite a declarar:** com o modelo roteirizado, testa-se o encanamento, não a decisão
  do agente.
- **Regressão de demonstração:** `matriz(..., [v2, v2.sem("contrato")])` mostra o teste
  do contrato ficando vermelho.

### N4.4 — Resiliência: falhas injetadas
- **Pergunta:** o sistema aguenta as falhas do NB03?
- **Técnica:** `tests/test_resiliencia.py` com modelo roteirizado + `falhas.injetar`:
  ferramenta fora → escala; 429 ×2 → conclui; primário fora → fallback; resultado ambíguo
  → limite; reinício com pendência → retoma; `timeout_apos_efeito` → um reembolso.
- **Resultado:** só a `v3` passa tudo; é o que diferencia `v2` de `v3` na matriz.

### N4.5 — Trajetória: modelo real, repetido
- **Pergunta:** o agente escolhe as ferramentas certas, na ordem certa, de forma estável?
- **Técnica:** (a) `AgentEvaluator.evaluate` / `adk eval` com
  `evals/trajetoria.evalset.json` e `tool_trajectory_avg_score` em modo `IN_ORDER`;
  (b) `tests/test_trajetoria.py` roda cada caso 5 vezes e mede a **taxa de estabilidade**
  com `ferramenta_antes(...)` e `chamou(...)`.
- **Resultado:** tabela de taxa por caso × versão. `# requer: live`.

### N4.6 — Qualidade da resposta
- **Avaliadores programáticos** (`tests/test_qualidade.py`): limite respeitado, PII ausente,
  solução ∈ permitidas para a categoria, valor dentro da regra.
- **Juiz (LLM-as-judge)** só para o que regra não pega: tom adequado. Usa
  `RANGOJA_MODELO_JUIZ`, de outro tamanho/família que o agente.
- **Validação do juiz:** `evals/rotulos_tom.yaml` (30 respostas rotuladas por cada
  apresentador separadamente). Relatar concordância humano×humano (kappa de Cohen) e
  juiz×consenso. Um juiz não validado é mais um modelo não testado.
- **Alternativa do ADK a mencionar:** `rubric_based_final_response_quality_v1`.
- **Resultado:** tabela critério × versão; concordância do juiz.

### N4.7 — Relações metamórficas
- **Pergunta:** entradas equivalentes produzem a mesma decisão?
- **Invariância:** `C01` e as variantes `C01-giria`, `C01-digitacao`, `C01-ordem`,
  `C01-ruido` têm a mesma `categoria` e a mesma `solucao`, com valor igual.
- **Monotonicidade:** `C02-40`, `C02-70`, `C02-120`: a compensação total não diminui com o
  atraso.
- **Conceito:** sem saber a resposta certa, sabemos como duas respostas devem se
  relacionar. Esta é a falha "variação diante de entradas equivalentes" do PDC.
- **Resultado:** violações por versão, 5 repetições. `# requer: live`. Se a medição não
  encontrar violação, relatar a taxa, manter o teste e ilustrar uma violação com roteiro,
  dizendo que é roteiro.
- **Experimente:** escrever uma relação nova (ex.: trocar o nome do restaurante não muda a
  decisão).

### N4.8 — Temperatura 0 resolve?
- Rodar `C01` e `C01-giria` 10 vezes cada, com temperatura padrão e com temperatura 0.
- **Conceito:** temperatura baixa reduz a variação entre execuções idênticas, mas não a
  elimina em API hospedada, e não faz nada pela variação entre entradas equivalentes.
  Por isso N4.5 e N4.7 existem.
- **Resultado:** número de decisões distintas por configuração. `# requer: live`.

### N4.9 — Tudo no CI
- Exibir `.github/workflows/ci.yml`:
  - todo push: `nbmake` dos notebooks em `replay`, `test_orquestracao.py`,
    `test_resiliencia.py`, `test_qualidade.py` (programáticos) contra `v3`;
  - agendado/manual (com chave como segredo): `test_trajetoria.py`, juiz,
    `test_metamorficos.py`, `adk eval`.
- Critério de falha: qualquer teste determinístico; nos estatísticos, taxa abaixo do limite
  configurado (ex.: estabilidade < 0,8).

### N4.10 — Recapitulação e próximos passos
Tabela final: as 3 falhas do PDC × a técnica que as detecta (variação → metamórficas;
desvio de fluxo → trajetória; contrato → orquestração roteirizada). Próximos passos:
monitoramento online e drift (as métricas do Phoenix ao longo do tempo), execução durável
(extra `x5`).
