"""O agente montado à mão na N1.1 (LlmAgent + Runner, sem atalhos) roda em replay e é o mesmo da v0."""
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from rangoja import dados
from rangoja.notebook import gravacao
from rangoja.versoes import v0

PROMPT = ("Você atende clientes do RangoJá, um app de delivery. Responda em português, com cordialidade e objetividade."
          "\n\nPolítica de atendimento:\n"
          + "\n\n".join(f"## {tema}\n{texto}" for tema, texto in dados.politica_secoes().items()))


def test_prompt_da_n11_e_o_da_v0():
    assert v0.construir().agente_raiz.instruction == PROMPT


def test_agente_cru_responde_com_a_gravacao_em_replay(monkeypatch):
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    agente = LlmAgent(name="unico", model=gravacao("N1.1/falha"), instruction=PROMPT)

    async def rodar():
        runner = Runner(app_name="rangoja", agent=agente, session_service=InMemorySessionService())
        sessao = await runner.session_service.create_session(app_name="rangoja", user_id="101")
        msg = types.Content(role="user", parts=[types.Part(text="Meu pedido 4821 chegou frio e faltou o refri.")])
        return [ev async for ev in runner.run_async(user_id="101", session_id=sessao.id, new_message=msg)]

    eventos = asyncio.run(rodar())
    textos = [p.text for ev in eventos if ev.content for p in ev.content.parts if p.text]
    assert textos and "voucher de R$ 15" in textos[-1]
    assert not any(p.function_call for ev in eventos if ev.content for p in ev.content.parts)


def _rodar_cru(agente):
    async def rodar():
        runner = Runner(app_name="rangoja", agent=agente, session_service=InMemorySessionService())
        sessao = await runner.session_service.create_session(app_name="rangoja", user_id="101")
        msg = types.Content(role="user", parts=[types.Part(text="Meu pedido 4821 chegou frio e faltou o refri.")])
        return [p.text for ev in [e async for e in runner.run_async(user_id="101", session_id=sessao.id, new_message=msg)]
                if ev.content for p in ev.content.parts if p.text]
    return asyncio.run(rodar())


def test_agente_cru_ignora_a_gravacao_deixada_por_atender(monkeypatch):
    """Rodar outra seção antes (atender deixa a gravação no contexto) não pode mudar o agente da N1.1."""
    from rangoja.execucao import atender
    from rangoja.notebook import preparar_secao
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    s = preparar_secao("N1.2")
    atender(s.correcao, s.caso, gravacao=s.gravacoes["correcao"])
    agente = LlmAgent(name="unico", model=gravacao("N1.1/falha"), instruction=PROMPT)
    assert "voucher de R$ 15" in _rodar_cru(agente)[-1]


def test_agente_cru_pode_rodar_duas_vezes(monkeypatch):
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    agente = LlmAgent(name="unico", model=gravacao("N1.1/falha"), instruction=PROMPT)
    assert _rodar_cru(agente)[-1] == _rodar_cru(agente)[-1]


def test_gravacao_repete_mesmo_em_live(monkeypatch):
    """gravacao() tem um só significado: repete a gravação, qualquer que seja o modo (sem rede)."""
    monkeypatch.setenv("RANGOJA_MODO", "live")
    agente = LlmAgent(name="unico", model=gravacao("N1.1/falha"), instruction=PROMPT)
    assert "voucher de R$ 15" in _rodar_cru(agente)[-1]
