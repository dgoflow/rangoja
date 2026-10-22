"""Estado da chave de API: o que a tabela do NB00 mostra e quando o modo live liga."""
import pytest

from rangoja import config


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    monkeypatch.setattr(config, "_validadas", {})
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RANGOJA_MODO", "replay")


def test_sem_chave_continua_em_replay():
    assert config.estado_chave() == "não (use replay)"
    assert config.usar_live() == "sem chave: continua em replay"
    assert config.modo() == "replay"


@pytest.mark.parametrize("resposta,inicio", [(True, "sim, validada"), (False, "sim, mas a OpenAI"), (None, "sim, não validada")])
def test_estado_da_chave(monkeypatch, resposta, inicio):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: resposta)
    assert config.estado_chave().startswith(inicio)


def test_chave_recusada_nao_liga_live(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: False)
    assert "recusou" in config.usar_live()
    assert config.modo() == "replay"


def test_chave_valida_liga_live(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: True)
    assert config.usar_live() == "modo live ligado neste kernel"
    assert config.modo() == "live"


def test_validacao_so_uma_vez_por_chave(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    chamadas = []
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: chamadas.append(1) or True)
    config.estado_chave()
    config.estado_chave()
    assert len(chamadas) == 1


def test_configurar_chave_sem_teclado_nao_trava(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda *a, **k: (_ for _ in ()).throw(EOFError()))
    assert "continua em replay" in config.configurar_chave()
