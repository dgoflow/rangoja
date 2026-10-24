"""Nomes que se leem: versões com título e descrição, atender_caso, afirmar e esperar."""
import pytest

from rangoja import notebook
from rangoja.casos import caso
from rangoja.execucao import atender, atender_caso
from rangoja.versoes import (APELIDOS, resolver, v0, v0_so_prompt, v1, v1_agente, v2, v2_controlado, v3,
                             v3_robusto)


def test_apelidos_sao_as_mesmas_versoes():
    assert (v0_so_prompt, v1_agente, v2_controlado, v3_robusto) == (v0, v1, v2, v3)
    assert APELIDOS == {"v0": "v0_so_prompt", "v1": "v1_agente", "v2": "v2_controlado", "v3": "v3_robusto"}


def test_titulo_legivel():
    assert v0.titulo == "v0_so_prompt"
    assert v0.com("ferramentas", "schema").titulo == "v0_so_prompt + ferramentas + schema"
    assert v1.sem("memoria_livre").titulo == "v1_agente − memoria_livre"


def test_o_nome_curto_continua_a_chave():
    assert v0.com("ferramentas").nome == "v0+ferramentas"
    assert resolver("v1+aprovacao").nome == "v1+aprovacao"


def test_resolver_aceita_o_nome_semantico():
    assert resolver("v2_controlado") == v2
    assert resolver("v1_agente-memoria_livre") == v1.sem("memoria_livre")


def test_descricao_da_versao_ao_digitar_o_nome():
    texto = repr(v0_so_prompt)
    assert texto.startswith("v0_so_prompt: só o prompt") and "prompt: agente sem ferramentas" in texto
    html = v1_agente._repr_html_()
    assert "<b>v1_agente</b>" in html and "<code>ferramentas</code>" in html


def test_atender_caso_e_atender_com_nomes_que_se_leem(monkeypatch):
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    a = atender_caso("C01", com=v0_so_prompt, replay="N1.1/falha")
    b = atender(v0, caso("C01"), gravacao="N1.1/falha")
    assert (a.resposta, a.fonte, a.status) == (b.resposta, b.fonte, b.status)


def test_resumo_mostra_o_titulo(capsys, monkeypatch):
    monkeypatch.setattr(notebook, "display", None)
    monkeypatch.setenv("RANGOJA_MODO", "replay")
    notebook.resumo(atender_caso("C01", com=v0_so_prompt, replay="N1.1/falha"))
    assert "v0_so_prompt" in capsys.readouterr().out


def test_afirmar_interrompe_e_os_nomes_antigos_seguem_valendo(capsys, monkeypatch):
    monkeypatch.setattr(notebook, "display", None)
    notebook.afirmar(True, "ok")
    with pytest.raises(AssertionError):
        notebook.afirmar(False, "falhou")
    assert notebook.verificar is notebook.afirmar
    assert notebook.conferir is notebook.esperar and notebook.verificar_falha is notebook.esperar
