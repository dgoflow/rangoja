"""Gera NB03 (falhas e observabilidade) e NB04 (testes e avaliação)."""
from _nb import code, md, salvar, setup


def nb03():
    return [
        md("# NB03 — Falhas e observabilidade\n\n**Pergunta:** o que acontece quando algo dá errado, e como eu vejo?  \n"
           "**Ideia central:** robustez é continuar se comportando bem quando algo falha. Só dá para tratar o que se consegue ver.\n\n"
           "Todas as falhas deste notebook são **induzidas** (`falhas.injetar`) sobre respostas de modelo *roteirizadas*: queremos falhar na hora certa, de forma reproduzível."),
        setup(),
        code("from rangoja.observabilidade import anatomia\ndef total(pedido):\n    return float(Armazem.atual().total_reembolsado(pedido))"),

        md("## N3.0 — Ligando a observabilidade\n\nO NB00 ligou o Phoenix, se disponível. Cada chamada ao modelo e cada ferramenta vira um *span*. Sem Phoenix, a `anatomia` mostra a mesma árvore em texto."),
        code('''s = preparar_secao("N3.0")
a = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
resumo(a)
print(anatomia(a))
print("\\nPhoenix:", observabilidade.url() or "indisponível (usando a anatomia em texto)")
verificar(a.status == "concluido" and a.estado.get("pedido_consultado") == "4821",
          "na sequência, o pedido é consultado em código antes do modelo agir, e o atendimento conclui")'''),

        md("## N3.1 — O trace mostra o desvio de fluxo\n\nCaso `C03`. A resposta final parece correta; só a trajetória revela que o reembolso aconteceu **sem consultar o pedido**."),
        code('''s = preparar_secao("N3.1")
falha = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
print(anatomia(falha))
verificar(not ferramenta_antes(falha.trajetoria, "buscar_pedido", "registrar_reembolso"), "o trace mostra reembolso sem consulta prévia")
Armazem.reset()
correcao = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
verificar(correcao.estado.get("pedido_consultado") == "6002", "na sequência, a consulta acontece antes de qualquer ação do modelo")'''),
        md("`ferramenta_antes` vira teste no NB04."),

        md("## N3.2 — Ferramenta fora do ar\n\nCaso `C03`, com `buscar_pedido` fora do ar. Sem tratamento, a exceção derruba o atendimento. A correção: o erro vira **resultado** que o agente entende, e o agente escala para um humano. Degradar para um humano é uma resposta robusta, não um fracasso."),
        code('''s = preparar_secao("N3.2")
with falhas.injetar("ferramenta_fora", alvo="buscar_pedido"):
    falha = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
resumo(falha)
verificar(falha.status == "erro", "sem tratamento, o atendimento termina em erro")'''),
        code('''mostrar(controle.erro_estruturado)
Armazem.reset()
with falhas.injetar("ferramenta_fora", alvo="buscar_pedido"):
    correcao = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
resumo(correcao)
verificar(correcao.status == "escalado" and total("6002") == 0.0, "com erro estruturado: escalou para um humano, sem reembolso")'''),

        md("## N3.3 — Modelo indisponível\n\nCaso `C02`. Duas falhas: 429 (limite de requisições) duas vezes seguidas, e o modelo primário fora do ar. Correções: **retry** com espera crescente e **fallback** para o modelo secundário."),
        code('''s = preparar_secao("N3.3")
with falhas.injetar("modelo_429", vezes=2):
    falha = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
resumo(falha)
verificar(falha.status == "erro", "sem retry, o primeiro 429 derruba o atendimento")'''),
        code('''from rangoja.modelo import pilha
mostrar(pilha.ModeloRangoja._chamar)
Armazem.reset()
with falhas.injetar("modelo_429", vezes=2):
    com_retry = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
resumo(com_retry)
print("tentativas por chamada ao modelo:", com_retry.tentativas)
verificar(com_retry.status == "concluido" and 3 in com_retry.tentativas, "com retry: duas falhas, terceira tentativa passou")
Armazem.reset()
with falhas.injetar("modelo_fora"):
    com_fallback = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
print("modelos usados:", sorted(set(com_fallback.modelos_usados)))
verificar(com_fallback.status == "concluido" and "secundario" in com_fallback.modelos_usados, "com fallback: o modelo secundário atendeu")'''),
        md("Em produção, `retry` e `fallback` vêm do cliente do provedor ou de um roteador como o LiteLLM. Aqui são código visível para o ponto ficar claro."),

        md("## N3.4 — O agente que não para\n\nCaso `C01`, com `buscar_pedido` devolvendo sempre *\"resultado incompleto, tente de novo\"*. O agente insiste. A correção é um **limite**: no máximo 3 chamadas por ferramenta; passando disso, escala."),
        code('''s = preparar_secao("N3.4")
with falhas.injetar("resultado_ambiguo", alvo="buscar_pedido"):
    falha = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
print("chamadas de buscar_pedido (sem limite):", contar_chamadas(falha.trajetoria, "buscar_pedido"))
verificar(contar_chamadas(falha.trajetoria, "buscar_pedido") == 4, "sem limite, o agente chamou a mesma ferramenta 4 vezes")
mostrar(controle.limite_ferramenta)
Armazem.reset()
with falhas.injetar("resultado_ambiguo", alvo="buscar_pedido"):
    correcao = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
resumo(correcao)
verificar(contar_chamadas(correcao.trajetoria, "buscar_pedido") <= 3 and correcao.status == "escalado", "com limite: no máximo 3 chamadas e escalou")'''),

        md("## N3.5 — O processo caiu com um reembolso pendente\n\nCaso `C09`. O reembolso de R$ 120 aguarda aprovação. O processo cai. A **fila de aprovação** está no armazém e sempre sobrevive; a **conversa** só sobrevive se a sessão estiver num banco."),
        code('''s = preparar_secao("N3.5")
a = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
verificar(a.status == "aguardando_aprovacao", "pendência criada")
reiniciar_runner(a)
print("estado da conversa depois da queda (sessão em memória):", estado_persistido(a))
try:
    continuar(a, "E aí, aprovaram?")
except RuntimeError as exc:
    print("continuar a conversa falhou:", exc)
verificar(estado_persistido(a) is None, "sem persistência, a conversa se perdeu")'''),
        code('''Armazem.reset()
b = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
reiniciar_runner(b)
persistido = estado_persistido(b)
print("estado da conversa depois da queda (SQLite):", {k: persistido[k] for k in ("cliente_id", "pedido_id") if k in persistido})
verificar(persistido is not None, "com persistência, a sessão sobreviveu à queda")
fechado = aprovar(b)
verificar(total("9001") == 120.0 and fechado.status == "concluido", "o supervisor aprova depois da queda: exatamente um reembolso de R$ 120")'''),

        md("## N3.6 — Reembolso em dobro\n\nCaso `C03`. O reembolso é feito, mas a **confirmação se perde** (timeout depois do efeito). O agente vê um erro e chama de novo. Frameworks e filas garantem *pelo menos uma vez*; *exatamente uma vez* é responsabilidade do sistema: **idempotência**."),
        code('''s = preparar_secao("N3.6")
with falhas.injetar("timeout_apos_efeito", alvo="registrar_reembolso"):
    falha = atender(s.falha, s.caso, roteiro=s.roteiro(s.falha))
resumo(falha)
print("total reembolsado no pedido 6002 (cobrança de R$ 42,90):", total("6002"))
verificar(abs(total("6002") - 85.8) < 0.01, "sem idempotência: o cliente foi reembolsado duas vezes")'''),
        code('''mostrar(ferramentas.efetivar_reembolso)
Armazem.reset()
with falhas.injetar("timeout_apos_efeito", alvo="registrar_reembolso"):
    correcao = atender(s.correcao, s.caso, roteiro=s.roteiro(s.correcao))
resumo(correcao)
verificar(abs(total("6002") - 42.9) < 0.01, "com idempotência: a segunda chamada devolveu o resultado da primeira, um único reembolso")'''),

        md("## N3.7 — Recapitulação\n\n| Falha injetada | Reação do sistema | Onde se vê |\n|---|---|---|\n| `buscar_pedido` fora do ar | erro vira resultado; escala | span da ferramenta com erro |\n| 429 do modelo (2×) | retry com espera | tentativas por chamada |\n| modelo primário fora | fallback para o secundário | `modelos_usados` |\n| ferramenta devolve sempre \"incompleto\" | limite de 3 chamadas; escala | contagem na trajetória |\n| queda do processo | fila de aprovação e sessão sobrevivem | `estado_persistido` |\n| confirmação perdida após o efeito | idempotência: um único reembolso | total no armazém |\n\nNão implementado aqui: métricas agregadas do Phoenix (taxa de erro de ferramenta, de escalonamento, latência).\n\n**Ponte para o NB04:** o sistema reage bem *a estes casos*. Como garantir que continua reagindo depois da próxima mudança?"),
    ]


def nb04():
    return [
        md("# NB04 — Testes e avaliação\n\n**Pergunta:** como provar que funciona sem saber a resposta certa?\n\n"
           "A ideia deste notebook é rodar a **mesma bateria de testes contra as versões** e ver os testes passarem à medida que o sistema amadurece. "
           "Cada técnica responde a uma pergunta diferente: comportamento, uso de ferramentas e qualidade das respostas.\n\n"
           "Legenda: ✅ passa · ❌ falha · ➖ não se aplica ou exige modelo ao vivo."),
        setup(),
        code('''import json, yaml
def relatorios_v3():
    saida = {}
    for arquivo in sorted((config.GRAVACOES / "v3").glob("*.json")):
        saida[arquivo.stem] = json.loads(arquivo.read_text(encoding="utf-8"))
    return saida
rel = relatorios_v3()
print(len(rel), "casos gravados com o modelo real em", config.modelo_primario())'''),

        md("## N4.1 — O problema do oráculo\n\nA mesma reclamação, com palavras diferentes, deve levar à mesma decisão. Mas **qual** é a decisão certa? Não há um texto esperado. Veja o que o modelo real fez com `C01` e suas variantes (gíria, digitação, ordem, ruído):"),
        code('''for c in ["C01", "C01-giria", "C01-digitacao", "C01-ordem", "C01-ruido"]:
    d = rel[c]["decisao"] or {}
    print(f"{c:15s} {d.get('categoria')!s:15s} {d.get('solucao')!s:15s} valor={d.get('valor')}")
print()
print("resposta ao cliente (C01):", (rel["C01"]["resposta"] or "")[:200])'''),
        md("Não vamos testar um texto exato. Vamos testar **comportamento esperado** e **relações entre saídas**. (O contraexemplo do juiz genérico de \"utilidade\" não foi implementado nesta versão.)"),

        md("## N4.2 — Critérios do domínio e golden dataset\n\nEm vez de uma nota genérica, **critérios do domínio**: decisão conforme a política; nada irreversível sem autorização; golpe sempre encaminhado; nenhuma PII do entregador; nenhum direito gravado na memória. "
           "O *golden dataset* guarda, para cada caso, o **comportamento esperado** (categoria, soluções permitidas, ferramentas obrigatórias e proibidas, ordem, status), não um texto."),
        code('''golden = yaml.safe_load((config.RAIZ / "evals" / "golden.yaml").read_text(encoding="utf-8"))
print(len(golden), "casos")
for g in golden[:6]:
    e = g["esperado"]
    print(f"{g['id']:8s} categoria={e.get('categoria')!s:15s} status={e.get('status')!s:22s} obrigatórias={e.get('ferramentas_obrigatorias')}")'''),
        md("Os critérios vieram de **análise de erros**: rotular falhas de traces reais e agrupá-las. Foi assim que se chegou às três falhas do projeto de origem (variação diante de entradas equivalentes, desvio de fluxo, quebra silenciosa de contrato)."),

        md("## N4.3 — Orquestração: modelo roteirizado\n\n**Pergunta:** dado que o modelo decidiu X, o sistema faz a coisa certa? O modelo é um *roteiro* (inclusive tentando o errado); callbacks, ferramentas e orquestração rodam de verdade. Rápido, barato, determinístico: roda em todo commit."),
        code('''t = matriz("test_orquestracao.py", [v1, v2, v3])
t'''),
        code('''verificar(all(l[3] == "✅" for l in t.linhas), "v3 passa toda a orquestração")
verificar(any(l[1] == "❌" for l in t.linhas), "v1 falha onde o controle importa")'''),
        md("**Limite a declarar:** com o modelo roteirizado, testa-se o encanamento, não a decisão do agente."),

        md("## N4.4 — Resiliência: falhas injetadas\n\n**Pergunta:** o sistema aguenta as falhas do NB03?"),
        code('''t = matriz("test_resiliencia.py", [v2, v3])
t'''),
        code('''verificar(all(l[2] == "✅" for l in t.linhas), "v3 passa toda a resiliência")
verificar(all(l[1] == "❌" for l in t.linhas), "v2 falha em todas: é o que a v3 acrescenta")'''),

        md("## N4.5 — Trajetória\n\n**Pergunta:** o agente usa as ferramentas certas, na ordem certa? Aqui, a ordem e as ferramentas em roteiros. A **estabilidade** com o modelo real é o teste `live` (marcado ➖ abaixo): ele repete o caso várias vezes e exige uma taxa mínima de trajetórias corretas."),
        code('''t = matriz("test_trajetoria.py", [v1, v2, v3])
t'''),
        md("A diferença entre v1 e v2 está no `desvio de fluxo`: com a sequência, a consulta do pedido é feita em código."),

        md("## N4.6 — Qualidade da resposta\n\n**Avaliadores programáticos**: regras verificáveis (limite respeitado, PII ausente, solução permitida, valor, ordem…). Abaixo, a bateria sobre o golden com modelo roteirizado, e depois o que o **modelo real** (v3) fez nos mesmos casos."),
        code('''t = matriz("test_qualidade.py", [v1, v2, v3])
t'''),
        code('''ok = [c for c, r in rel.items() if not r["reprovados"] and r["status"] != "erro"]
print(f"modelo real, v3: {len(ok)} de {len(rel)} casos sem nenhuma regra reprovada\\n")
for c, r in rel.items():
    print(f"{'OK ' if c in ok else '!! '}{c:15s} status={r['status']:22s} reprovados={list(r['reprovados'])}")'''),
        md("Estes resultados são **do modelo real e variam entre execuções**. Muitas reprovações são o modelo escolhendo uma solução diferente da esperada (por exemplo `voucher` onde esperávamos `reembolso`), e algumas indicam que a expectativa é estrita demais. Uma avaliação serve para te mostrar isso, não para dar nota boa."),
        md("*O juiz de tom (LLM-as-judge) e a medida de concordância com rótulos humanos não foram implementados nesta versão.*"),

        md("## N4.7 — Relações metamórficas\n\n**Pergunta:** entradas equivalentes levam à mesma decisão? Sem saber a resposta certa, sabemos como duas respostas devem se relacionar.\n\n- **Invariância:** gíria, erro de digitação, outra ordem ou um detalhe irrelevante não mudam a decisão.\n- **Monotonicidade:** mais atraso nunca reduz a compensação."),
        code('''t = matriz("test_metamorficos.py", [v2, v3])
t'''),
        md("Esses testes verificam o **detector** (com um modelo roteirizado, uma violação plantada tem que ser pega e uma relação respeitada não pode dar alarme). O modelo real está abaixo, com as decisões gravadas para o grupo `C01`:"),
        code('''def assinatura(c):
    d = rel[c]["decisao"] or {}
    return (d.get("categoria"), d.get("solucao"), d.get("valor"))
base = assinatura("C01")
print("origem C01:", base)
for c in ["C01-giria", "C01-digitacao", "C01-ordem", "C01-ruido"]:
    marca = "igual   " if assinatura(c) == base else "DIFERE  "
    print(marca, c, assinatura(c))'''),
        md("Uma diferença aqui é uma **violação metamórfica real**: o sistema decide diferente para uma reclamação equivalente. É exatamente a falha *variação diante de entradas equivalentes*."),

        md("## N4.8 — Temperatura 0 resolve?\n\nTemperatura baixa reduz a variação entre execuções idênticas, mas **não a elimina** em API hospedada, e não faz nada pela variação entre entradas *equivalentes* (N4.7). Esta medição exige o modelo ao vivo e **não foi executada** nesta versão."),

        md("## N4.9 — Tudo no CI\n\nA ideia: testes determinísticos (esta bateria com modelo roteirizado) em todo push; os com modelo real (`pytest -m live`, com `RANGOJA_MODO=live` e a chave) agendados, por causa do custo. Isso está em `.github/workflows/`: `ci.yml` roda a bateria determinística, os notebooks em `replay` e a conferência das gravações; `avaliacao.yml` roda os testes `live`, agendados."),

        md("## N4.10 — Recapitulação\n\n| Falha do projeto de origem | Técnica que a detecta | Onde |\n|---|---|---|\n| Variação diante de entradas equivalentes | Relações metamórficas | N4.7 |\n| Desvio de fluxo | Asserções sobre a trajetória | N4.5 |\n| Quebra silenciosa de contrato | Orquestração roteirizada (contrato entre etapas) | N4.3 |\n\n**Próximos passos:** monitoramento online e drift (as métricas do Phoenix ao longo do tempo) e execução durável de fluxos longos."),
    ]


if __name__ == "__main__":
    print(salvar("03_falhas_e_observabilidade.ipynb", nb03()))
    print(salvar("04_testes_e_avaliacao.ipynb", nb04()))
