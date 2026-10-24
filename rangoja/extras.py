"""Auxiliares dos notebooks extras (x1 a x3). Nada aqui é usado pelas versões v0–v3.

x1: memória pesquisável (MemoryService do ADK) e a política do que pode virar memória.
x2: conversas longas (janela, resumo e estado estruturado).
x3: dados sintéticos para o golden dataset e variantes metamórficas.
"""
from __future__ import annotations

import difflib
import random
import re
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.load_memory_tool import load_memory_tool
from google.genai import types

from . import dados, politica
from .execucao import APP, _enviar, _mensagem, _nova_sessao, _rodar
from .modelo import contexto
from .modelo.pilha import ModeloRangoja
from .modelo.roteiro import Roteiro

# ---------------------------------------------------------------- x1: memória pesquisável


def nova_memoria() -> InMemoryMemoryService:
    """Memória em processo do ADK. Busca por palavras (sem embeddings): serve para o conceito."""
    return InMemoryMemoryService()


def _eventos_da_sessao(atendimento) -> list[Event]:
    sessao = _rodar(lambda: atendimento._servico.get_session(
        app_name=APP, user_id=atendimento.cliente_id, session_id=atendimento.sessao_id))
    return [e for e in sessao.events if e.content and e.content.parts]


def guardar_bruto(memoria, atendimento) -> int:
    """Política ingênua: a conversa inteira vira memória, inclusive o que o cliente alegou."""
    eventos = _eventos_da_sessao(atendimento)
    _rodar(lambda: memoria.add_events_to_memory(
        app_name=APP, user_id=atendimento.cliente_id, events=eventos, session_id=atendimento.sessao_id))
    return len(eventos)


def fatos_verificados(atendimento) -> list[str]:
    """O que o *código* sabe que aconteceu: efeitos reais das ferramentas, nunca falas do cliente."""
    fatos = []
    pedido = atendimento.estado.get("pedido_id")
    if pedido:
        fatos.append(f"Atendimento sobre o pedido {pedido}.")
    for c in atendimento.trajetoria:
        if not c.efetiva:
            continue
        if c.ferramenta == "registrar_reembolso":
            fatos.append(f"Reembolso de R$ {float(c.args.get('valor')):.2f} registrado no pedido {c.args.get('pedido_id')} "
                         f"(motivo: {c.args.get('motivo')}).")
        elif c.ferramenta == "oferecer_cupom":
            fatos.append(f"Cupom de R$ {float(c.args.get('valor')):.2f} concedido no pedido {c.args.get('pedido_id')}.")
        elif c.ferramenta == "solicitar_reenvio":
            fatos.append(f"Reenvio solicitado no pedido {c.args.get('pedido_id')}.")
        elif c.ferramenta in ("escalar_para_humano", "encaminhar_seguranca"):
            fatos.append(f"Caso encaminhado ({c.ferramenta}).")
    return fatos


def guardar_fatos(memoria, atendimento) -> list[str]:
    """Política segura: só entram fatos verificados, escritos pelo sistema."""
    fatos = fatos_verificados(atendimento)
    eventos = [Event(author="atendimento", content=types.Content(role="model", parts=[types.Part(text=f)]))
               for f in fatos]
    if eventos:
        _rodar(lambda: memoria.add_events_to_memory(
            app_name=APP, user_id=atendimento.cliente_id, events=eventos, session_id=atendimento.sessao_id))
    return fatos


@dataclass
class Consulta:
    pergunta: str
    resposta: str | None
    memorias: list[str] = field(default_factory=list)   # o que a ferramenta devolveu ao modelo
    consultas: list[str] = field(default_factory=list)  # as buscas que o modelo fez


def perguntar_com_memoria(cliente_id: str, pergunta: str, memoria, roteiro: dict) -> Consulta:
    """Agente com a ferramenta `load_memory`. O modelo é roteirizado (`roteiro`): o que se testa é a
    memória (o que foi guardado e o que a busca devolve), não a redação da resposta."""
    agente = LlmAgent(
        name="memoria", model=ModeloRangoja(agente="memoria"), tools=[load_memory_tool],
        instruction=("Você atende clientes do RangoJá. Para lembrar de atendimentos anteriores do cliente, "
                     "use load_memory. Cite só o que a memória trouxer; se não trouxe, diga que não há registro."))
    servico = InMemorySessionService()
    runner = Runner(app_name=APP, agent=agente, session_service=servico, memory_service=memoria)
    contexto.definir(contexto.Contexto(roteiro=Roteiro(roteiro)))
    sessao = _nova_sessao(servico, cliente_id)
    eventos, erro = _rodar(lambda: _enviar(runner, cliente_id, sessao, _mensagem(pergunta), _config()))
    if erro:
        raise RuntimeError(erro)
    c = Consulta(pergunta, None)
    for ev in eventos:
        for p in (ev.content.parts if ev.content and ev.content.parts else []):
            if p.function_call and p.function_call.name == "load_memory":
                c.consultas.append((p.function_call.args or {}).get("query", ""))
            elif p.function_response and p.function_response.name == "load_memory":
                c.memorias.extend(_textos_da_memoria(p.function_response.response or {}))
            elif p.text and ev.author == "memoria":
                c.resposta = p.text
    return c


def _textos_da_memoria(resposta: dict[str, Any]) -> list[str]:
    """A ferramenta devolve {'result': LoadMemoryResponse} (objeto) ou, serializada, {'memories': [...]}."""
    resultado = resposta.get("result", resposta)
    memorias = getattr(resultado, "memories", None)
    if memorias is None:
        memorias = resultado.get("memories", []) if isinstance(resultado, dict) else []
    textos = []
    for m in memorias:
        conteudo = m["content"] if isinstance(m, dict) else m.content
        partes = conteudo["parts"] if isinstance(conteudo, dict) else conteudo.parts
        textos.extend((p["text"] if isinstance(p, dict) else p.text) for p in partes
                      if (p.get("text") if isinstance(p, dict) else p.text))
    return textos


def _config():
    from google.adk.agents.run_config import RunConfig
    return RunConfig(max_llm_calls=10)


# ---------------------------------------------------------------- x2: conversas longas


def tokens(texto: str) -> int:
    """Estimativa grosseira (1 token ≈ 4 caracteres). Serve para comparar estratégias, não para cobrar."""
    return max(1, len(texto) // 4)


Turno = tuple[str, str]  # (papel, texto)

_CONVERSA_FIXA: list[Turno] = [
    ("cliente", "Meu pedido chegou incompleto."),
    ("atendente", "Sinto muito! Pode me dizer o número do pedido e o que faltou?"),
    ("cliente", "É o 4822, faltou o refri."),
    ("atendente", "Consultei o pedido 4822. Reembolsei R$ 8,00 do refrigerante."),
    ("cliente", "Ah, e faltou a sobremesa também."),
    ("atendente", "Concedi um cupom de R$ 10,00 pela sobremesa que faltou. Total compensado: R$ 18,00."),
]
_CONVERSA_LIVRE: list[Turno] = [
    ("cliente", "Valeu! Aproveitando, o app tá lento aqui comigo."),
    ("atendente", "Obrigado por avisar. Esse tipo de problema vai para a equipe do aplicativo."),
    ("cliente", "Vocês entregam no bairro vizinho também?"),
    ("atendente", "A cobertura aparece no app, na tela de endereço, antes de você fechar o pedido."),
    ("cliente", "E se eu quiser trocar o endereço de um pedido já feito?"),
    ("atendente", "Depois que o restaurante aceita, a troca não é possível; o suporte pode ajudar caso a caso."),
    ("cliente", "Entendi. Tem programa de fidelidade?"),
    ("atendente", "Hoje não temos programa de pontos, mas cupons aparecem na aba de ofertas."),
    ("cliente", "Beleza. E o horário de atendimento?"),
    ("atendente", "O atendimento por chat funciona todos os dias, no horário comercial."),
    ("cliente", "Ok. Posso pagar com vale-refeição?"),
    ("atendente", "Sim, os principais vales aparecem como opção no pagamento."),
    ("cliente", "Show. Última: o entregador pode deixar na portaria?"),
    ("atendente", "Pode, desde que você marque a opção de entrega na portaria ao fazer o pedido."),
    ("cliente", "Perfeito, era só isso."),
    ("atendente", "Combinado! Qualquer coisa é só chamar."),
]


def conversa_longa(turnos: int = 20) -> list[Turno]:
    """Conversa sintética a partir do C11: 6 turnos reais do caso e o restante de assunto solto.
    O pedido e as compensações aparecem só no começo, como acontece em atendimentos longos."""
    return (_CONVERSA_FIXA + _CONVERSA_LIVRE)[:turnos]


def texto_da_conversa(conversa: list[Turno]) -> str:
    return "\n".join(f"{papel}: {fala}" for papel, fala in conversa)


def janela_deslizante(conversa: list[Turno], ultimos: int) -> list[Turno]:
    return conversa[-ultimos:]


# Resumo escrito à mão, no estilo de um resumo genérico de modelo: fluido e sem os números.
RESUMO_GENERICO = (
    "O cliente relatou que um pedido chegou incompleto, com itens faltando. A atendente pediu detalhes, "
    "resolveu a situação com compensações e o cliente agradeceu. Depois, tirou dúvidas sobre cobertura, "
    "troca de endereço, fidelidade, horário e formas de pagamento."
)


def fatos_na_conversa(texto: str, estado: dict[str, Any]) -> dict[str, bool]:
    """Os fatos que o código precisa para continuar: o pedido e quanto já foi compensado."""
    pedido, valor = estado.get("pedido_id"), estado.get("compensacoes")  # ao vivo, o modelo pode não ter chegado lá
    formas = {f"{valor:.2f}".replace(".", ","), f"{valor}"} if valor is not None else set()
    return {"pedido_id": pedido is not None and str(pedido) in texto, "compensado": any(f in texto for f in formas)}


def contexto_com_estado(estado: dict[str, Any], conversa: list[Turno], ultimos: int) -> str:
    """Contexto enxuto: estado estruturado (fonte de verdade) + janela curta da conversa."""
    campos = {k: estado[k] for k in ("pedido_id", "compensacoes") if k in estado}
    return f"ESTADO: {campos}\n" + texto_da_conversa(janela_deslizante(conversa, ultimos))


# ---------------------------------------------------------------- x3: dados sintéticos

PERSONAS = ["formal", "giria", "apressado", "irritado", "detalhista"]

# cenário -> (categoria esperada, modelos de reclamação; {p} é o pedido; None = sem pedido)
CENARIOS: dict[str, tuple[str, list[str], str | None]] = {
    "item_faltando_bebida": ("item_faltando", ["Meu pedido {p} chegou sem a bebida.", "Faltou o refrigerante do pedido {p}."], "4821"),
    "item_faltando_sobremesa": ("item_faltando", ["No pedido {p} faltou a sobremesa.", "A sobremesa do pedido {p} não veio."], "4822"),
    "atraso": ("atraso", ["O pedido {p} atrasou muito.", "O pedido {p} demorou mais de uma hora para chegar."], "5310"),
    "cobranca_dobro": ("cobranca", ["Fui cobrado duas vezes no pedido {p}.", "O pedido {p} foi cobrado em dobro no cartão."], "6002"),
    "qualidade": ("qualidade", ["A comida do pedido {p} chegou fria.", "O pedido {p} veio gelado e sem gosto.", "O pedido {p} chegou sem tempero, praticamente cru.", "O pedido {p} chegou com a embalagem aberta."], "4821"),
    "golpe": ("golpe", ["Recebi uma ligação dizendo ser do RangoJá pedindo um pix, foi golpe sobre o pedido {p}."], "7730"),
    "fora_do_escopo": ("fora_do_escopo", ["Me passa uma receita de bolo de cenoura.", "Qual a previsão do tempo para amanhã?"], None),
}

_GIRIA = {"pedido": "rango", "chegou": "veio", "muito": "pra caramba", "fria": "gelada", "comida": "comida", "meu": "o meu"}
_RUIDO = ["Tava chovendo aqui.", "Já é a terceira vez que peço aí.", "Estou em casa com a família."]


def estilizar(texto: str, persona: str, rng: random.Random) -> str:
    if persona == "formal":
        return "Prezados, " + texto[0].lower() + texto[1:] + " Solicito providências."
    if persona == "giria":
        return "mano, " + _aplicar_giria(texto).rstrip(".") + "!!"
    if persona == "apressado":
        return re.sub(r"[.,]", "", texto).lower()
    if persona == "irritado":
        return texto.upper().rstrip(".") + "!!! ISSO É UM ABSURDO"
    return texto + " " + rng.choice(_RUIDO) + " Peço que verifiquem com atenção."  # detalhista


def _aplicar_giria(texto: str) -> str:
    return " ".join(_GIRIA.get(p.lower(), p) for p in texto.split())


@dataclass
class Sintetico:
    id: str
    persona: str
    cenario: str
    texto: str
    categoria_esperada: str
    pedido_id: str | None
    motivo: str | None = None   # preenchido quando o filtro automático rejeita


def gerar_reclamacoes(semente: int = 7, por_celula: int = 3) -> list[Sintetico]:
    """Persona × cenário. Em produção um modelo escreve as reclamações; aqui são modelos de frase
    estilizados, para o notebook ser reproduzível e de graça."""
    rng = random.Random(semente)
    saida: list[Sintetico] = []
    for cenario, (categoria, modelos, pedido) in CENARIOS.items():
        for persona in PERSONAS:
            for i in range(por_celula):
                base = rng.choice(modelos).format(p=pedido or "")
                saida.append(Sintetico(f"S{len(saida) + 1:03d}", persona, cenario, estilizar(base, persona, rng),
                                       categoria, pedido))
    return saida


def normalizar(texto: str) -> set[str]:
    return set(re.findall(r"[a-zà-ú0-9]+", texto.lower()))


def similaridade(a: str, b: str) -> float:
    x, y = normalizar(a), normalizar(b)
    return len(x & y) / len(x | y) if x | y else 1.0


def deduplicar(itens: list[Sintetico], limiar: float = 0.8) -> tuple[list[Sintetico], list[tuple[Sintetico, Sintetico]]]:
    """Mantém o primeiro de cada grupo de quase-duplicatas (Jaccard de palavras ≥ limiar)."""
    mantidos: list[Sintetico] = []
    descartados: list[tuple[Sintetico, Sintetico]] = []
    for item in itens:
        igual = next((m for m in mantidos if similaridade(m.texto, item.texto) >= limiar), None)
        if igual is None:
            mantidos.append(item)
        else:
            descartados.append((item, igual))
    return mantidos, descartados


_PALAVRAS: dict[str, list[str]] = {
    "golpe": ["golpe", "fraude", "pix"],
    "cobranca": ["cobrado", "cobraram", "cobrança", "dobro", "duas vezes"],
    "item_faltando": ["faltou", "faltando", "falta", "sumiu", "veio sem", "chegou sem", "não veio"],
    "item_errado": ["errado", "outro sabor", "trocaram"],
    "atraso": ["atrasou", "atraso", "demorou", "demora"],
    "qualidade": ["frio", "fria", "gelado", "gelada", "azedo", "estragado"],
}


def _tem(palavra: str, tokens_: list[str], texto: str) -> bool:
    if " " in palavra:
        return palavra in texto
    return bool(difflib.get_close_matches(palavra, tokens_, n=1, cutoff=0.8))


def classificar_por_palavras(texto: str) -> str:
    """Classificador de referência barato (palavras-chave com tolerância a erro de digitação). Não é o
    agente: serve para checar se uma variante preserva o sentido e para sinalizar o que um humano revisa."""
    baixo = texto.lower()
    tokens_ = re.findall(r"[a-zà-ú]+", baixo)
    achadas = [cat for cat, palavras in _PALAVRAS.items() if any(_tem(p, tokens_, baixo) for p in palavras)]
    if not achadas:
        return "fora_do_escopo"
    return politica.categoria_principal(achadas)


def filtrar(itens: list[Sintetico]) -> tuple[list[Sintetico], list[Sintetico]]:
    """Filtro automático: o classificador de referência concorda com a categoria pedida, e o pedido existe.
    Rejeitados vão para revisão humana (com o motivo), não para o lixo."""
    ok, revisar = [], []
    for item in itens:
        previsto = classificar_por_palavras(item.texto)
        if item.pedido_id and dados.pedido(item.pedido_id) is None:
            item.motivo = f"pedido {item.pedido_id} não existe"
        elif previsto != item.categoria_esperada:
            item.motivo = f"referência classificou como {previsto}, esperado {item.categoria_esperada}"
        (revisar if item.motivo else ok).append(item)
    return ok, revisar


# Transformações metamórficas: as quatro primeiras devem preservar o sentido; as duas últimas são
# defeituosas de propósito, para mostrar que a checagem as pega.
def _trocar_letras(texto: str) -> str:
    palavras = texto.split()
    for i, p in enumerate(palavras):
        if len(p) > 5 and i % 3 == 1:
            palavras[i] = p[0] + p[2] + p[1] + p[3:]
    return " ".join(palavras)


def _ordem(texto: str) -> str:
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if f.strip()]
    return " ".join(reversed(frases)) if len(frases) > 1 else texto + " Pode verificar?"


TRANSFORMACOES = {
    "giria": lambda t: "mano, " + _aplicar_giria(t),
    "digitacao": _trocar_letras,
    "ordem": _ordem,
    "ruido": lambda t: t + " Tava chovendo aqui.",
    "inversao (defeituosa)": lambda t: re.sub(r"[Ff]altou|faltando", "sobrou", t, count=1).replace("chegou sem", "chegou com"),
    "truncamento (defeituosa)": lambda t: t.split(" ")[0] + " " + t.split(" ")[1] if len(t.split(" ")) > 2 else t,
}


def preserva_sentido(original: Sintetico, variante: str) -> tuple[bool, str]:
    """Aceita a variante se o pedido citado continua lá e a categoria de referência não mudou."""
    if original.pedido_id and original.pedido_id not in variante:
        return False, "perdeu o número do pedido"
    previsto = classificar_por_palavras(variante)
    if previsto != original.categoria_esperada:
        return False, f"categoria virou {previsto}"
    return True, "ok"
