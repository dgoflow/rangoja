"""comparar() lê dos agentes construídos o que muda entre versões: prompt, ferramentas, schema, callbacks, execução."""
import pytest

from rangoja import notebook
from rangoja.secoes import SECOES


@pytest.fixture
def saida(monkeypatch, capsys):
    monkeypatch.setattr(notebook, "display", None)

    def rodar(secao_id):
        s = SECOES[secao_id]
        notebook.comparar(s.falha, s.correcao)
        return capsys.readouterr().out
    return rodar


def test_ferramentas_entram_e_o_prompt_muda(saida):
    texto = saida("N1.2")
    assert "+ buscar_pedido(enxuta=False)" in texto
    assert "+ Consulte os fatos com as ferramentas" in texto


def test_schema(saida):
    assert "saída estruturada: — → Decisao" in saida("N1.4")


def test_mudanca_fora_do_agente_aparece_na_execucao(saida):
    texto = saida("N1.5")
    assert "Agente\n  igual" in texto
    assert "sessão: uma nova a cada mensagem → uma por atendimento" in texto


def test_opcao_da_ferramenta(saida):
    texto = saida("N2.1")
    assert "+ registrar_reembolso(com_aprovacao=True, idempotente=False)" in texto


def test_callback(saida):
    assert "before_model_callback: — → guardrail_entrada" in saida("N2.2")


def test_ficha_completa_sem_antes(monkeypatch, capsys):
    monkeypatch.setattr(notebook, "display", None)
    from rangoja.versoes import v0
    notebook.comparar(None, v0)
    texto = capsys.readouterr().out
    assert texto.startswith("Ficha de v0") and "Política de atendimento" in texto
