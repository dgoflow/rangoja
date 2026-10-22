"""Gera NB00 e NB01. Textos em português; o que depende de gravação é calculado nas células."""
from _nb import code, md, salvar, setup


def nb00():
    return [
        md("# NB00 — Ambiente\n\nVerifica se você consegue rodar os outros notebooks. **Tudo funciona sem chave de API**, em modo `replay`: "
           "as respostas do modelo vêm de gravações feitas com o modelo real. Só N0.1, N0.2 e N0.6 são bloqueantes."),
        setup(),
        md("## N0.1 — Versões"),
        code('''import sys, importlib.metadata as meta
for pacote in ["google-adk", "litellm", "arize-phoenix", "openinference-instrumentation-google-adk", "pydantic"]:
    try:
        print(f"{pacote:45s} {meta.version(pacote)}")
    except meta.PackageNotFoundError:
        print(f"{pacote:45s} (não instalado)")
verificar(sys.version_info >= (3, 11), "Python 3.11 ou mais novo")
verificar(meta.version("google-adk") == "1.33.0", "google-adk 1.33.0")'''),
        md("## N0.2 — Replay: respostas gravadas do modelo real"),
        code('''s = preparar_secao("N1.1")
a = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(a)
verificar(a.erro is None and set(a.fonte) == {"gravacao"}, "o atendimento rodou só com a gravação, sem rede e sem chave")'''),
        md("## N0.3 — Chave de API (opcional)\n\nSem chave você acompanha tudo em `replay`. Para rodar ao vivo, execute a célula abaixo: se já houver chave (no `.env`), ela liga o modo `live`; se não houver, pede sua `OPENAI_API_KEY` com entrada oculta. Cada notebook tem seu próprio kernel: a chave vale só para este, a menos que você aceite **salvá-la no `.env`** (fora do git) quando a célula perguntar."),
        code('''if not config.chave_disponivel():
    print(config.diagnostico_chave())
    print(config.configurar_chave())  # Enter vazio: segue em replay
elif config.modo() == "replay":
    print(config.usar_live())  # há chave: liga o modo ao vivo neste kernel
print("modelo:", config.modelo_primario(), "| modo:", config.modo())
print("chave de API:", config.estado_chave())'''),
        md("## N0.4 — Observabilidade (Phoenix)\n\nO Phoenix é opcional. Sem ele, os notebooks mostram a trajetória em texto."),
        code('''print(observabilidade.ligar())
print("interface:", observabilidade.url() or "indisponível")'''),
        md("## N0.5 — Como o agente roda\n\nOs notebooks usam o `Runner` do ADK como biblioteca, dentro deste processo: não há servidor nem API a subir. `atender(...)` monta o agente da versão, roda o `Runner` e devolve o resultado. As interfaces `adk web` e `adk api_server` não fazem parte deste material."),
        md("## N0.6 — A suíte de testes (determinística)"),
        code('''tabela = matriz("test_orquestracao.py", [v3])
print(tabela)
verificar(all(linha[1] == "✅" for linha in tabela.linhas), "todos os testes de orquestração passam na v3")'''),
        md("## N0.7 — Resumo\n\nSe N0.1, N0.2 e N0.6 passaram, você está pronto. Se algo falhou, veja o `SETUP.md`."),
    ]


def nb01():
    return [
        md("# NB01 — Do prompt ao agente\n\n**Pergunta:** o que separa um prompt de um agente?  \n"
           "**Caminho:** `v0` (agente sem ferramentas, com a política colada) → `v1` (ferramentas, decisão estruturada, estado, contexto enxuto, memória).\n\n"
           "Cada seção mostra um problema real do RangoJá e a correção. As execuções vêm de **gravações do modelo real**; "
           "quando uma gravação foi escolhida entre várias, a célula diz a taxa."),
        setup(),
        md("## N1.1 — O prompt que funciona na demo\n\n"
           "Antes de qualquer atalho, o agente inteiro, em ADK puro. Primeiro, o que chegou: a reclamação do cliente e o pedido como ele está no sistema."),
        code('''mensagem = "Meu pedido 4821 chegou frio e faltou o refri."

pedido = dados.pedido("4821")
for item in pedido.itens:
    print(f"{item.nome:22s} R$ {float(item.preco):6.2f}   {'entregue' if item.entregue else 'NÃO entregue'}")
print(f"{'total':22s} R$ {float(pedido.total):6.2f}")'''),
        md("O agente é um `LlmAgent` do ADK: um nome, um modelo e uma instrução. Aqui a instrução é o prompt com a política inteira colada. "
           "O modelo vem do `.env`: em `live`, o `LiteLlm` chama o modelo de `RANGOJA_MODELO` com a sua chave; em `replay`, uma gravação do modelo real responde no lugar dele.\n\n"
           "As linhas comentadas são os **pontos de intervenção**: os lugares onde o código pode agir sobre o agente. Cada seção do material preenche um deles."),
        code('''from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from rangoja.notebook import gravacao

politica = "\\n\\n".join(f"## {tema}\\n{texto}" for tema, texto in dados.politica_secoes().items())
PROMPT = ("Você atende clientes do RangoJá, um app de delivery. Responda em português, com cordialidade e objetividade."
          "\\n\\nPolítica de atendimento:\\n" + politica)

if config.modo() == "replay":
    llm = gravacao("N1.1/falha")  # sem chave: o que o modelo real respondeu quando gravamos
else:
    llm = LiteLlm(model=f"openai/{config.modelo_primario()}")  # o modelo de RANGOJA_MODELO (.env), com a sua chave

agente = LlmAgent(
    name="unico",
    model=llm,
    instruction=PROMPT,
    # tools=[buscar_pedido, registrar_reembolso, ...]   ← N1.2  ferramentas trazem fatos e agem
    # output_schema=Decisao                             ← N1.4  decisão que o código consegue ler
    # before_model_callback=guardrail_entrada           ← N2.2  filtra o que chega ao modelo
    # after_model_callback=guardrail_saida              ← N2.3  filtra o que sai para o cliente
    # before_tool_callback=limite_ferramenta            ← N2.4, N3.4  autoriza cada ação
    # on_tool_error_callback=erro_estruturado           ← N3.2  erro de ferramenta vira resultado
)
print(f"modelo: {'gravação N1.1/falha' if config.modo() == 'replay' else config.modelo_primario() + ' ao vivo'}")
print(f"instrução com {len(PROMPT)} caracteres; ferramentas: {len(agente.tools)}")'''),
        md("Para rodar, o `Runner` do ADK conduz o loop: entrega a mensagem ao agente, chama o modelo e devolve **eventos**. A sessão guarda a conversa."),
        code('''from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService  # ← N3.5: SqliteSessionService sobrevive à queda do processo
from google.genai import types

runner = Runner(app_name="rangoja", agent=agente, session_service=InMemorySessionService())
sessao = await runner.session_service.create_session(app_name="rangoja", user_id="101")
pergunta = types.Content(role="user", parts=[types.Part(text=mensagem)])

chamadas, resposta_v0 = [], None
async for evento in runner.run_async(user_id="101", session_id=sessao.id, new_message=pergunta):
    for parte in (evento.content.parts if evento.content else []):
        if parte.function_call:
            chamadas.append(parte.function_call.name)
            print(f"[{evento.author}] chama {parte.function_call.name}({dict(parte.function_call.args)})")
        if parte.text:
            resposta_v0 = parte.text
            print(f"[{evento.author}] {parte.text}")'''),
        md("**Parece certo, e é esse o problema.** A resposta segue a política (voucher de até R$ 15 por qualidade, reembolso do item que faltou). "
           "Mas o agente acreditou no cliente sem olhar o pedido, não registrou reembolso nenhum, e a resposta não diz quanto: o código não tem o que executar."),
        code('''verificar(not chamadas, "nenhuma ferramenta chamada: o agente não consultou o pedido nem registrou o reembolso")
verificar(agente.output_schema is None, "a saída é só texto: não há decisão (categoria, valor) que o código possa ler")
print("a resposta cita um valor de reembolso?", "R$ 8" in (resposta_v0 or ""))'''),
        md("Daqui em diante usamos um **atalho**. `atender(v0, caso)` monta este mesmo agente e roda este mesmo `Runner`; "
           "`preparar_secao` escolhe o caso, a versão e a gravação de cada seção e começa com um armazém limpo."),
        code('''s = preparar_secao("N1.1")
verificar(s.falha.construir().agente_raiz.instruction == PROMPT, "a v0 usa exatamente o PROMPT montado acima")
falha = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(falha)
amostra(s.gravacoes["falha"])'''),
        md("O modelo só sabe o que está no contexto. Texto plausível não é fato. Como dar fatos ao modelo? **Ferramentas.**"),

        md("## N1.2 — Ferramentas trazem fatos\n\nA mesma reclamação, agora com ferramentas (`buscar_pedido`, `consultar_politica`, cupom, reembolso…). A docstring e os tipos de cada função são o que o modelo lê."),
        code('''s = preparar_secao("N1.2")
mostrar(ferramentas._fabrica_buscar_pedido(enxuta=True))
correcao = atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
resumo(correcao)
amostra(s.gravacoes["correcao"])'''),
        code('''registrados = [c.args.get("valor") for c in correcao.trajetoria if c.ferramenta == "registrar_reembolso"]
print("consultou o pedido?", chamou(correcao.trajetoria, "buscar_pedido"))
print("reembolsos registrados:", registrados, "| valor real do refrigerante: R$ 8,00")
verificar_falha(correcao, correcao.erro is None and bool(correcao.trajetoria), "com ferramentas, o agente passou a agir no sistema")'''),
        md("**Achado das gravações:** ter ferramentas disponíveis **não garante** que o modelo as use para consultar os fatos. Nesta configuração (política colada na instrução, resposta em texto), nenhuma das 6 execuções gravadas consultou o pedido, e os valores que o modelo registrou não batem com ele. "
           "Isso muda nas próximas seções: com a decisão estruturada (N1.4) e o estado da conversa (N1.5), a versão de falha da N1.6 consultou o pedido em 5 de 6 execuções; com o contexto enxuto, em 6 de 6. Com 6 amostras, não dá para separar o efeito de cada componente."),

        md("## N1.3 — O loop por baixo\n\nUm agente é um loop: o modelo pede uma ferramenta, a ferramenta responde, o modelo decide o próximo passo ou responde. Os eventos do ADK mostram isso."),
        code('''from rangoja.observabilidade import anatomia
s = preparar_secao("N1.3")
a = atender(s.correcao, s.caso, gravacao="N1.2/correcao")
print(anatomia(a))
passos = [ev for ev in a.eventos if ev.content and ev.content.parts]
verificar(len(passos) >= 2, "há pelo menos dois passos: o modelo age e o sistema responde")'''),

        md("## N1.4 — Prosa × estrutura\n\nCaso `C02` (atraso). O agente decide em **prosa**: o código não tem como extrair categoria e valor. A correção é um **contrato**: a decisão é estruturada (`Decisao`) e a resposta ao cliente continua em texto."),
        code('''s = preparar_secao("N1.4")
falha = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(falha); amostra(s.gravacoes["falha"])
verificar_falha(falha, falha.decisao is None, "em prosa, o código não recebe uma decisão utilizável")'''),
        code('''from rangoja import tipos
mostrar(tipos.Decisao)
correcao = atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
resumo(correcao); amostra(s.gravacoes["correcao"])
verificar_falha(correcao, correcao.decisao is not None, "a decisão agora é um objeto tipado")
verificar_falha(correcao, correcao.decisao.solucao in __import__("rangoja.politica", fromlist=["x"]).solucoes_permitidas(correcao.decisao.categoria),
                "a solução decidida existe na política para a categoria")'''),
        md("Nota: com a API do ADK, a saída estruturada chega por uma ferramenta interna (`set_model_response`). Ela aparece nos eventos e é ignorada nas funções de trajetória."),

        md("## N1.5 — Estado da conversa\n\nCaso `C11`: três mensagens (sem pedido → o 4822, faltou o refri → \"e a sobremesa também\"). Sem estado, cada mensagem abre uma sessão nova."),
        code('''s = preparar_secao("N1.5")
falha = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(falha); amostra(s.gravacoes["falha"])
print("estado da última sessão (sem estado):", {k: v for k, v in falha.estado.items() if k in ("pedido_id", "compensacoes")})'''),
        code('''correcao = atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
resumo(correcao); amostra(s.gravacoes["correcao"])
print("estado da sessão (com estado):", {k: v for k, v in correcao.estado.items() if k in ("pedido_id", "compensacoes")})
verificar_falha(correcao, correcao.estado.get("pedido_id") == "4822", "o estado guardou o pedido da conversa")
verificar_falha(falha, falha.estado.get("pedido_id") != "4822", "sem estado, a última sessão não sabe qual é o pedido")'''),

        md("## N1.6 — O que entra no contexto\n\n"
           "Caso `C01`, agora quase na `v1`: ferramentas, decisão estruturada e estado, mas **sem o contexto enxuto**. "
           "`buscar_pedido` devolve o pedido inteiro, inclusive os dados do entregador, que o modelo não precisa para decidir."),
        code('''s = preparar_secao("N1.6")
falha = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(falha); amostra(s.gravacoes["falha"])
buscas = [c for c in falha.trajetoria if c.ferramenta == "buscar_pedido"]
if buscas:
    print("o que o modelo recebeu sobre o entregador:", buscas[0].resultado.get("entregador"))
    verificar_falha(falha, "entregador" in buscas[0].resultado, "nome, telefone e placa do entregador entraram no contexto do modelo")
else:
    print("nesta execução o modelo não consultou o pedido")'''),
        md("**A resposta está certa, e é por isso que o problema passa despercebido.** O dado do entregador não aparece na resposta, mas está no contexto: o modelo pode repeti-lo a qualquer momento. "
           "Em N2.3 simulamos esse vazamento (nas 10 execuções reais, o modelo não vazou) e vemos o guardrail de saída barrá-lo. "
           "Aqui a correção vem antes: a ferramenta devolve só o que a decisão precisa."),
        code('''correcao = atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
resumo(correcao); amostra(s.gravacoes["correcao"])
buscas = [c for c in correcao.trajetoria if c.ferramenta == "buscar_pedido"]
if buscas:
    print("campos devolvidos ao modelo (versão enxuta):", sorted(buscas[0].resultado.keys()))
    verificar_falha(correcao, "entregador" not in buscas[0].resultado, "com o contexto enxuto, nenhum dado do entregador chega ao modelo")
else:
    print("nesta execução o modelo não consultou o pedido")'''),

        md("## N1.7 — Lembrar do cliente\n\nCaso `C13`: dois atendimentos do mesmo cliente. No primeiro ele diz que prefere a entrega na portaria. Sem memória, o segundo atendimento não sabe."),
        code('''s = preparar_secao("N1.7")
falha = atender(s.falha, s.caso, gravacao=s.gravacoes["falha"])
resumo(falha); amostra(s.gravacoes["falha"])
verificar_falha(falha, "portaria" not in (falha.resposta or "").lower(), "sem memória, o segundo atendimento não menciona a portaria")'''),
        code('''mostrar(ferramentas.anotar_observacao)
correcao = atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
resumo(correcao); amostra(s.gravacoes["correcao"])
print("observações guardadas para o cliente:", correcao.estado.get("user:observacoes"))
verificar_falha(correcao, "portaria" in (correcao.resposta or "").lower(), "com memória, o agente usa a preferência")'''),
        md("Atenção: **memória livre é uma porta de entrada**. No NB02 vemos o cliente usá-la para gravar um direito que não tem."),

        md("## N1.8 — Recapitulação\n\n| Problema | Componente | Onde |\n|---|---|---|\n| O modelo inventa fatos | `ferramentas` | `rangoja/ferramentas.py` |\n| Decisão em prosa | `schema` | `rangoja/tipos.py` (`Decisao`) |\n| A conversa se perde | `estado` | `session.state` |\n| Contexto cheio de dados que não servem | `contexto_enxuto` | `ferramentas._resumo_enxuto` |\n| O agente não lembra do cliente | `memoria_livre` | `user:observacoes` |\n\n**Ponte para o NB02:** o agente agora age e lembra. Nada ainda o impede de agir mal."),
    ]


if __name__ == "__main__":
    print(salvar("00_ambiente.ipynb", nb00()))
    print(salvar("01_do_prompt_ao_agente.ipynb", nb01()))
