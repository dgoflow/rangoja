"""O modo decide de onde vem a resposta do modelo: replay usa gravação; live e record usam o modelo de verdade."""
import pytest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from rangoja import notebook
from rangoja.casos import caso
from rangoja.execucao import atender
from rangoja.modelo import pilha
from rangoja.versoes import v0


@pytest.fixture
def modelo_ao_vivo(monkeypatch):
    chamadas = []

    async def falso(modelo, requisicao):
        chamadas.append(modelo.agente)
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="resposta do modelo ao vivo")]))

    monkeypatch.setattr(pilha, "_ao_vivo", falso)
    return chamadas


def test_replay_usa_a_gravacao_e_nao_chama_o_modelo(monkeypatch, modelo_ao_vivo):
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    a = atender(v0, caso("C01"), gravacao="N1.1/falha")
    assert a.fonte == ["gravacao"] and not modelo_ao_vivo
    assert "voucher de R$ 15" in a.resposta


@pytest.mark.parametrize("modo", ["live", "record"])
def test_live_e_record_ignoram_a_gravacao(monkeypatch, modelo_ao_vivo, tmp_path, modo):
    monkeypatch.setenv("RANGOJA_MODO", modo)
    monkeypatch.setattr(pilha.config, "CACHE", tmp_path)  # record grava o cache: fora do repositório
    a = atender(v0, caso("C01"), gravacao="N1.1/falha")
    assert a.fonte == ["live"] and modelo_ao_vivo == ["unico"]
    assert a.resposta == "resposta do modelo ao vivo"


def test_live_nao_usa_o_cache(monkeypatch, modelo_ao_vivo, tmp_path):
    monkeypatch.setattr(pilha.config, "CACHE", tmp_path)
    monkeypatch.setenv("RANGOJA_MODO", "record")
    atender(v0, caso("C01"))  # grava o cache
    modelo_ao_vivo.clear()
    monkeypatch.setenv("RANGOJA_MODO", "live")
    a = atender(v0, caso("C01"))
    assert a.fonte == ["live"] and modelo_ao_vivo == ["unico"]


def test_roteiro_vale_em_qualquer_modo(monkeypatch, modelo_ao_vivo):
    """Roteiro simula uma falha que o modelo real não deu: não pode sumir em live."""
    from rangoja.modelo import texto
    monkeypatch.setenv("RANGOJA_MODO", "live")
    a = atender(v0, caso("C01"), roteiro={"unico": [texto("resposta do roteiro")]})
    assert a.fonte == ["roteiro"] and not modelo_ao_vivo
    assert a.resposta == "resposta do roteiro"


class _Atendimento:
    def __init__(self, fonte):
        self.fonte = fonte


def test_esperar_afirma_com_gravacao_e_so_avisa_ao_vivo(capsys, monkeypatch):
    monkeypatch.setattr(notebook, "display", None)
    with pytest.raises(AssertionError):
        notebook.esperar(_Atendimento(["gravacao"]), False, "x")
    notebook.esperar(_Atendimento(["live"]), False, "isso aconteceu")   # não interrompe
    notebook.esperar(_Atendimento(["live"]), True, "isso aconteceu")
    saida = capsys.readouterr().out
    assert "⚠️ isso aconteceu: não se confirmou desta vez" in saida
    assert "✅ isso aconteceu (modelo ao vivo)" in saida
