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


def test_em_modo_vale_so_dentro_do_bloco(monkeypatch):
    monkeypatch.setenv("RANGOJA_MODO", "live")
    with config.em_modo("replay"):
        assert config.modo() == "replay"
    assert config.modo() == "live"
    with pytest.raises(RuntimeError), config.em_modo("replay"):
        raise RuntimeError
    assert config.modo() == "live"


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


def test_gravar_env_preserva_o_resto_e_restringe_permissao(tmp_path):
    arq = tmp_path / ".env"
    arq.write_text("# nota\nOPENAI_API_KEY=\n# RANGOJA_MODO=replay\nRANGOJA_MODELO=gpt-4o-mini\n", encoding="utf-8")
    config.gravar_env({"OPENAI_API_KEY": "sk-x", "RANGOJA_MODO": "live"}, arq)
    assert arq.read_text(encoding="utf-8").splitlines() == [
        "# nota", "OPENAI_API_KEY=sk-x", "RANGOJA_MODO=live", "RANGOJA_MODELO=gpt-4o-mini"]
    assert oct(arq.stat().st_mode & 0o777) == "0o600"


def test_gravar_env_cria_o_arquivo(tmp_path):
    arq = config.gravar_env({"OPENAI_API_KEY": "sk-x"}, tmp_path / ".env")
    assert arq.read_text(encoding="utf-8") == "OPENAI_API_KEY=sk-x\n"


def test_configurar_chave_pergunta_e_salva(monkeypatch, tmp_path):
    monkeypatch.setattr("getpass.getpass", lambda *a, **k: "sk-digitada")
    monkeypatch.setattr("builtins.input", lambda *a: "s")
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: True)
    msg = config.configurar_chave(arquivo=tmp_path / ".env")
    assert "salva em" in msg and "sk-digitada" not in msg
    assert "OPENAI_API_KEY=sk-digitada" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_configurar_chave_por_padrao_nao_salva(monkeypatch, tmp_path):
    monkeypatch.setattr("getpass.getpass", lambda *a, **k: "sk-digitada")
    monkeypatch.setattr("builtins.input", lambda *a: "")
    monkeypatch.setattr(config, "validar_chave", lambda chave, timeout=0: True)
    msg = config.configurar_chave(arquivo=tmp_path / ".env")
    assert "vale só para este notebook" in msg and not (tmp_path / ".env").exists()


def test_configuracao_publica_do_modelo():
    """O NB00 e o pacote dependem destas funções; um reescrita de config.py não pode derrubá-las."""
    assert config.modelo_primario() and config.modelo_fallback() and config.modelo_juiz()
    assert config.repeticoes() >= 1 and 0 < config.limiar_estabilidade() <= 1


def test_preparar_ambiente_roda_sem_chave(monkeypatch):
    from rangoja import notebook
    monkeypatch.setenv("RANGOJA_PHOENIX", "off")
    notebook.preparar_ambiente()  # a célula de preparação do NB00 não pode quebrar
