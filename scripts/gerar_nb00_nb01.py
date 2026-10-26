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
afirmar(sys.version_info >= (3, 11), "Python 3.11 ou mais novo")
afirmar(meta.version("google-adk") == "1.33.0", "google-adk 1.33.0")'''),
        md("## N0.2 — Replay: respostas gravadas do modelo real\n\n"
           "Um atendimento inteiro, sem rede e sem chave. A resposta vem de uma gravação do gpt-4o-mini. Três coisas para conferir: "
           "o status, se houve decisão estruturada e de onde veio a resposta.\n\n"
           "Esta seção roda **sempre em `replay`**, mesmo que o seu `.env` esteja em `live`: é o caminho que a sala usa, "
           "e é ele que precisa funcionar. O modelo ao vivo aparece depois da N0.3."),
        code('''from IPython.display import Markdown, display

with config.em_modo("replay"):  # vale só dentro do bloco: com live no .env, o resto do notebook continua ao vivo
    a = atender_caso("C01", com=v0_so_prompt, replay="N1.1/falha")  # a resposta que o gpt-4o-mini deu quando gravamos
texto = " ".join((a.resposta or "—").split())
display(Markdown(
    f"**status:** {a.status}  \\n"
    f"**decisão:** {a.decisao or 'nenhuma: a resposta é só texto'}  \\n"
    f"**resposta:** {texto[:160]}{'…' if len(texto) > 160 else ''}  \\n"
    f"**origem:** {'gravação do gpt-4o-mini, sem rede' if set(a.fonte) == {'gravacao'} else a.fonte}"))'''),
        code('''afirmar(a.erro is None and set(a.fonte) == {"gravacao"}, "o atendimento rodou só com a gravação, sem rede e sem chave")
if config.modo() == "live":
    print("seu .env está em live: esta conferência foi em replay; o resto do notebook segue ao vivo")'''),
        md("## N0.3 — Chave de API (opcional)\n\nSem chave você acompanha tudo em `replay`. Para rodar ao vivo, execute a célula abaixo: se já houver chave (no `.env`), ela liga o modo `live`; se não houver, pede sua `OPENAI_API_KEY` com entrada oculta. Cada notebook tem seu próprio kernel: a chave vale só para este, a menos que você aceite **salvá-la no `.env`** (fora do git) quando a célula perguntar."),
        code('''if not config.chave_disponivel():
    print(config.diagnostico_chave())
    print(config.configurar_chave())  # Enter vazio: segue em replay
elif config.modo() == "replay":
    print(config.usar_live())  # há chave: liga o modo ao vivo neste kernel
print("modelo:", config.modelo_primario(), "| modo:", config.modo())
print("chave de API:", config.estado_chave())'''),
        md("Com o `live` ligado, a célula abaixo atende o mesmo cliente da N0.2, agora com o modelo respondendo. "
           "Compare com a gravação: a resposta muda de uma execução para outra. Em `replay` ela não chama o modelo."),
        code('''if config.modo() == "live":
    ao_vivo = atender_caso("C01", com=v0_so_prompt)  # sem replay=: o modelo responde agora (gasta tokens)
    texto_ao_vivo = " ".join((ao_vivo.resposta or "—").split())
    display(Markdown(
        f"**gravação (N0.2):** {texto[:160]}{'…' if len(texto) > 160 else ''}  \\n"
        f"**ao vivo, agora:** {texto_ao_vivo[:160]}{'…' if len(texto_ao_vivo) > 160 else ''}  \\n"
        f"**origem:** {config.modelo_primario()} ao vivo"))
    esperar(ao_vivo, ao_vivo.erro is None and "live" in ao_vivo.fonte, "o mesmo atendimento rodou com o modelo ao vivo")
else:
    print("modo replay: nada a comparar. Com a chave, esta célula mostra o mesmo atendimento respondido ao vivo.")'''),
        md("## N0.4 — Observabilidade (Phoenix)\n\nO Phoenix vem na instalação. Com `RANGOJA_PHOENIX=off`, ou se a porta 6006 estiver ocupada, os notebooks mostram a mesma trajetória em texto (a `anatomia`), sem perda de conteúdo."),
        code('''print(observabilidade.ligar())
print("interface:", observabilidade.url() or "indisponível")'''),
        md("## N0.5 — Como o agente roda\n\nOs notebooks usam o `Runner` do ADK como biblioteca, dentro deste processo: não há servidor nem API a subir. `atender_caso(...)` monta o agente da versão, roda o `Runner` e devolve o resultado. As interfaces `adk web` e `adk api_server` não fazem parte deste material."),
        md("## N0.6 — A suíte de testes (determinística)"),
        code('''tabela = matriz("test_orquestracao.py", [v3])
print(tabela)
afirmar(all(linha[1] == "✅" for linha in tabela.linhas), "todos os testes de orquestração passam na v3")'''),
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

async for evento in runner.run_async(user_id="101", session_id=sessao.id, new_message=pergunta):
    for parte in (evento.content.parts if evento.content else []):
        if parte.function_call:
            print(f"[{evento.author}] chama {parte.function_call.name}({dict(parte.function_call.args)})")
        if parte.text:
            print(f"[{evento.author}] {parte.text}")'''),
        md("**Parece certo, e é esse o problema.** A resposta gravada segue a política (voucher de até R$ 15 por qualidade, reembolso do item que faltou). "
           "Mas olhe o que aconteceu de fato:\n\n"
           "- **Nada foi consultado.** O agente acreditou no cliente: não tinha como saber se o refrigerante faltou mesmo, nem quanto custava.\n"
           "- **Nada foi feito.** O cliente leu \"reembolso\", mas não existe reembolso no sistema: o agente tem zero ferramentas. Ao vivo, o modelo às vezes ainda diz que está \"processando\".\n"
           "- **O código não tem o que executar.** A saída é texto: não há categoria nem valor que um sistema possa ler e cumprir.\n\n"
           "Funciona na demo. Não funciona em produção."),
        md("Daqui em diante usamos um **atalho**: `atender_caso(caso, com=agente, replay=...)` faz o que as duas células acima fizeram "
           "(monta o agente e roda o `Runner`) e devolve o resultado em campos que o código pode verificar. "
           "O `replay=` diz qual resposta gravada usar em modo `replay`, sem chave. Em modo `live`, ele é ignorado: o modelo responde de verdade. "
           "O agente é uma **versão**: um conjunto nomeado de componentes. Esta é a `v0_so_prompt`:"),
        code('''from rangoja.versoes import v0_so_prompt

v0_so_prompt  # digitar o nome de uma versão mostra o que ela é'''),
        code('''afirmar(v0_so_prompt.construir().agente_raiz.instruction == PROMPT, "v0_so_prompt é o agente montado acima (mesmo prompt)")

resultado = atender_caso("C01", com=v0_so_prompt, replay="N1.1/falha")  # C01: cliente 101, pedido 4821
# replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
print("decisão:             ", resultado.decisao)     # None: nada que o código possa ler
print("ferramentas chamadas:", resultado.trajetoria)  # []: o agente não consultou nem registrou nada
print("resposta veio de:    ", resultado.fonte)'''),
        code('''# 🎯 EXPERIMENTE: a ficha completa de uma versão, lida do agente construído (prompt, ferramentas, callbacks, execução)
# comparar(None, v0_so_prompt)'''),
        md("O modelo só sabe o que está no contexto. Texto plausível não é fato. Como dar fatos ao modelo? **Ferramentas.**"),

        md("## N1.2 — Ferramentas trazem fatos\n\n"
           "A mesma reclamação. Agora o agente ganha **ferramentas**: funções Python que o modelo pode pedir para executar, "
           "como `buscar_pedido` e `registrar_reembolso`. Primeiro, o que muda de um agente para o outro, lido dos próprios agentes:"),
        code('''sem_ferramentas = v0_so_prompt
com_ferramentas = v0_so_prompt.com("ferramentas")
comparar(sem_ferramentas, com_ferramentas)'''),
        md("Uma ferramenta é uma função Python comum. O modelo não vê o código: o ADK envia a ele só o **nome, a descrição (a docstring) e os parâmetros**, "
           "e o modelo decide se pede para chamá-la. É isto que ele recebe:"),
        code('''from google.adk.tools import FunctionTool

ferramentas_do_agente = {f.__name__: f for f in com_ferramentas.construir().agente_raiz.tools}
for nome, funcao in ferramentas_do_agente.items():
    print(f"{nome:22s} {funcao.__doc__}")

print("\\no que o ADK envia ao modelo sobre buscar_pedido:")
print(FunctionTool(ferramentas_do_agente["buscar_pedido"])._get_declaration().model_dump_json(exclude_none=True, indent=1))'''),
        code('''# 🎯 EXPERIMENTE: chame uma ferramenta você mesmo, como o ADK faria quando o modelo pede
# ferramentas.consultar_politica("atraso")'''),
        md("Agora o atendimento. As ferramentas agem num banco de pedidos e reembolsos; começamos com ele limpo."),
        code('''Armazem.reset()  # banco de pedidos e reembolsos limpo para esta seção
resultado = atender_caso("C01", com=com_ferramentas, replay="N1.2/correcao")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
resumo(resultado)

reembolsos = [c.args.get("valor") for c in resultado.trajetoria if c.ferramenta == "registrar_reembolso"]
print("consultou o pedido antes de agir?", chamou(resultado.trajetoria, "buscar_pedido"))
print("reembolsos registrados:", reembolsos, "| preço do refrigerante no pedido: R$ 8,00")'''),
        md("**O prompt pede, o modelo não obedece, e o código não percebe.** O prompt ganhou a frase *\"Consulte os fatos com as ferramentas antes de decidir. Nunca invente valores de pedido.\"* "
           "e o agente tem `buscar_pedido`. Mesmo assim, nenhuma das 6 execuções gravadas consultou o pedido, e na gravação usada em `replay` o modelo registrou R$ 5 de reembolso por um refrigerante de R$ 8. "
           "Ter ferramentas disponíveis **não garante** que o modelo as use. "
           "Isso muda nas próximas seções: com a decisão estruturada (N1.4) e o estado da conversa (N1.5), a versão de falha da N1.6 consultou o pedido em 5 de 6 execuções; com o contexto enxuto, em 6 de 6. Com 6 amostras, não dá para separar o efeito de cada componente."),

        md("## N1.3 — O loop por baixo\n\n"
           "Um agente é um loop: o modelo pede uma ferramenta, o sistema a executa e devolve o resultado, o modelo decide o próximo passo ou responde. "
           "`anatomia` mostra esse vaivém a partir dos eventos do ADK, na mesma resposta gravada da N1.2."),
        code('''from rangoja.observabilidade import anatomia

com_ferramentas = v0_so_prompt.com("ferramentas")
Armazem.reset()  # banco de pedidos e reembolsos limpo para esta seção
resultado = atender_caso("C01", com=com_ferramentas, replay="N1.2/correcao")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
print(anatomia(resultado))'''),

        md("## N1.4 — Prosa × estrutura\n\n"
           "Caso `C02` (atraso). Até aqui o agente decide em **prosa**: o código não tem como extrair a categoria e o valor da decisão. "
           "A correção é um **contrato**: a decisão sai num formato fixo (`Decisao`), e a mensagem ao cliente vai dentro dela, em texto. O que muda:"),
        code('''sem_schema = v0_so_prompt.com("ferramentas")
com_schema = sem_schema.com("schema")
comparar(sem_schema, com_schema)'''),
        code('''Armazem.reset()
em_prosa = atender_caso("C02", com=sem_schema, replay="N1.4/falha")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
resumo(em_prosa)
print("decisão que o código recebe:", em_prosa.decisao)'''),
        md("Este é o formato que a decisão passa a ter. O ADK o envia ao modelo e valida a resposta contra ele:"),
        code('''from rangoja.politica import solucoes_permitidas
from rangoja.tipos import Decisao
mostrar(Decisao)

Armazem.reset()
estruturada = atender_caso("C02", com=com_schema, replay="N1.4/correcao")
resumo(estruturada)
d = estruturada.decisao
if d is not None:
    print("categoria:", d.categoria, "| solução:", d.solucao, "| valor:", d.valor)
esperar(estruturada, d is not None and d.solucao in solucoes_permitidas(d.categoria),
         "o código consegue conferir a decisão: a solução existe na política para a categoria")'''),
        code('''# 🎯 EXPERIMENTE: o schema recusa o que está fora do contrato. Esta solução não existe na política:
# try:
#     Decisao.model_validate({"categoria": "atraso", "solucao": "pix_na_hora", "valor": 10, "pedido_id": "4822"})
# except Exception as erro:
#     print(erro)'''),
        md("Nota: no ADK, a saída estruturada chega por uma ferramenta interna (`set_model_response`). Ela aparece nos eventos, mas não conta como ferramenta do atendimento."),

        md("## N1.5 — Estado da conversa\n\n"
           "Caso `C11`: três mensagens do mesmo cliente. Sem estado, cada mensagem abre uma sessão nova, e o agente esquece o que veio antes. "
           "Aqui a mudança não está no agente, e sim em como a conversa roda:"),
        code('''sem_estado = v0_so_prompt.com("ferramentas", "schema")
com_estado = sem_estado.com("estado")
comparar(sem_estado, com_estado)

conversa = caso("C11")
for i, mensagem in enumerate(conversa.atendimentos[0], 1):
    print(f"mensagem {i}: {mensagem}")'''),
        code('''Armazem.reset()
esquece = atender_caso("C11", com=sem_estado, replay="N1.5/falha")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
resumo(esquece)
print("o que a última sessão sabe:", {k: v for k, v in esquece.estado.items() if k in ("pedido_id", "compensacoes")})'''),
        code('''Armazem.reset()
lembra = atender_caso("C11", com=com_estado, replay="N1.5/correcao")
resumo(lembra); amostra("N1.5/correcao")
print("o que a sessão sabe:", {k: v for k, v in lembra.estado.items() if k in ("pedido_id", "compensacoes")})
esperar(lembra, lembra.estado.get("pedido_id") == "4822", "com estado, a sessão guardou o pedido da conversa")'''),

        md("## N1.6 — O que entra no contexto\n\n"
           "Caso `C01` de novo. O agente já tem ferramentas, decisão estruturada e estado, mas `buscar_pedido` devolve **o pedido inteiro**, "
           "inclusive os dados do entregador, que o modelo não precisa para decidir. A correção é o **contexto enxuto**:"),
        code('''sem_enxuto = v0_so_prompt.com("ferramentas", "schema", "estado")
enxuto = sem_enxuto.com("contexto_enxuto")
comparar(sem_enxuto, enxuto)'''),
        code('''Armazem.reset()
completo = atender_caso("C01", com=sem_enxuto, replay="N1.6/falha")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
resumo(completo); amostra("N1.6/falha")
buscas = [c for c in completo.trajetoria if c.ferramenta == "buscar_pedido"]
if buscas:
    print("o que o modelo recebeu sobre o entregador:", buscas[0].resultado.get("entregador"))
else:
    print("nesta execução o modelo não consultou o pedido")'''),
        md("**A resposta está certa, e é por isso que o problema passa despercebido.** O dado do entregador não aparece na resposta, mas está no contexto: o modelo pode repeti-lo a qualquer momento. "
           "Em N2.3 simulamos esse vazamento (nas 10 execuções reais, o modelo não vazou) e vemos o guardrail de saída barrá-lo. "
           "Aqui a correção vem antes: a ferramenta devolve só o que a decisão precisa."),
        code('''Armazem.reset()
so_o_necessario = atender_caso("C01", com=enxuto, replay="N1.6/correcao")
resumo(so_o_necessario); amostra("N1.6/correcao")
buscas = [c for c in so_o_necessario.trajetoria if c.ferramenta == "buscar_pedido"]
if buscas:
    print("campos que o modelo recebeu:", sorted(buscas[0].resultado.keys()))
    afirmar("entregador" not in buscas[0].resultado, "com o contexto enxuto, nenhum dado do entregador chega ao modelo")
else:
    print("nesta execução o modelo não consultou o pedido")'''),
        code('''# 🎯 EXPERIMENTE: o que cada variante de buscar_pedido devolve para outro pedido, sem passar pelo modelo
# from rangoja.ferramentas import _completo, _resumo_enxuto
# print("completo:", sorted(_completo(dados.pedido("5310"))))
# print("enxuto:  ", sorted(_resumo_enxuto(dados.pedido("5310"))))'''),

        md("## N1.7 — Lembrar do cliente\n\n"
           "Caso `C13`: dois atendimentos do mesmo cliente, em dias diferentes. No primeiro ele diz que prefere a entrega na portaria. "
           "Sem memória, o segundo atendimento não sabe disso. A correção é uma **memória do cliente** (estado com o prefixo `user:`, que atravessa as sessões):"),
        code('''sem_memoria = v0_so_prompt.com("ferramentas", "schema", "estado", "contexto_enxuto")
com_memoria = sem_memoria.com("memoria_livre")  # esta é a v1_agente
comparar(sem_memoria, com_memoria)

cliente = caso("C13")
for i, mensagens in enumerate(cliente.atendimentos, 1):
    print(f"atendimento {i}: {mensagens}")'''),
        code('''Armazem.reset()
esquece = atender_caso("C13", com=sem_memoria, replay="N1.7/falha")  # replay: a resposta gravada do gpt-4o-mini; live: o modelo responde agora
resumo(esquece)
print("o segundo atendimento menciona a portaria?", "portaria" in (esquece.resposta or "").lower())'''),
        md("A memória entra por uma ferramenta nova, `anotar_observacao`: o modelo decide o que anotar, e o texto é gravado em `user:observacoes`, "
           "que volta no prompt do próximo atendimento (`{user:observacoes?}`). É isto que o modelo recebe sobre ela:"),
        code('''from google.adk.tools import FunctionTool
print(FunctionTool(ferramentas.anotar_observacao)._get_declaration().model_dump_json(exclude_none=True, indent=1))'''),
        code('''Armazem.reset()
lembra = atender_caso("C13", com=com_memoria, replay="N1.7/correcao")
resumo(lembra); amostra("N1.7/correcao")
print("observações guardadas para o cliente:", lembra.estado.get("user:observacoes"))
esperar(lembra, "portaria" in (lembra.resposta or "").lower(), "com memória, o segundo atendimento usa a preferência")'''),
        md("A taxa acima importa: com memória, o modelo **pode** usar a preferência, mas fez isso em poucas das execuções reais. "
           "E **memória livre é uma porta de entrada**: no NB02 vemos o cliente usá-la para gravar um direito que não tem."),

        md("## N1.8 — Recapitulação\n\n| Problema | Componente | Onde |\n|---|---|---|\n| O modelo inventa fatos | `ferramentas` | `rangoja/ferramentas.py` |\n| Decisão em prosa | `schema` | `rangoja/tipos.py` (`Decisao`) |\n| A conversa se perde | `estado` | `session.state` |\n| Contexto cheio de dados que não servem | `contexto_enxuto` | `ferramentas._resumo_enxuto` |\n| O agente não lembra do cliente | `memoria_livre` | `user:observacoes` |\n\n**Ponte para o NB02:** o agente agora age e lembra. Nada ainda o impede de agir mal."),
        code('''# 🎯 EXPERIMENTE: tudo o que o NB01 acrescentou, de uma vez
# comparar(v0_so_prompt, v1_agente)'''),
    ]


if __name__ == "__main__":
    print(salvar("00_ambiente.ipynb", nb00()))
    print(salvar("01_do_prompt_ao_agente.ipynb", nb01()))
