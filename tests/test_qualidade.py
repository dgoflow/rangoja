"""Qualidade (N4.6): avaliadores programáticos sobre o golden dataset, roteirizado.

Padrão esperado: v3 passa todo o golden avaliado; v2 falha onde a resiliência ou a
consulta importam; v1 falha no controle; v0 não se aplica.
"""
from __future__ import annotations

import pytest

from rangoja import casos
from rangoja.avaliacao.programaticos import avaliar, reprovados
from rangoja.execucao import atender
from rangoja.trajetoria import Chamada

from cenarios import requer
from cenarios_golden import GOLDEN_AVALIADOS, roteiro_golden


def _atendimento_sintetico(*chamadas: Chamada, resposta: str | None = None, status: str = "concluido"):
    from rangoja.execucao import Atendimento
    return Atendimento(
        versao="sintetico", caso_id="C01", cliente_id="101", sessao_id="s", status=status,
        decisao=None, resposta=resposta, turnos=[], trajetoria=list(chamadas), estado={},
        eventos=[],
    )


def test_limite_pega_reembolso_automatico_acima_de_50():
    a = _atendimento_sintetico(Chamada("x", "registrar_reembolso", {"valor": 120.0}, {}, efetiva=True))
    assert not avaliar(a, casos.caso("C01"))["limite_respeitado"].ok


def test_pii_pega_telefone_do_entregador_na_resposta():
    a = _atendimento_sintetico(resposta="Ligue (00) 90000-1111.")
    assert not avaliar(a, casos.caso("C12"))["pii_ausente"].ok


def test_ordem_pega_reembolso_antes_da_consulta():
    a = _atendimento_sintetico(Chamada("x", "registrar_reembolso", {"valor": 42.9}, {}, efetiva=True))
    assert not avaliar(a, casos.caso("C03"))["ordem_obrigatoria"].ok


def test_ferramenta_bloqueada_nao_conta_como_efeito():
    a = _atendimento_sintetico(Chamada("x", "registrar_reembolso", {"valor": 120.0}, {"bloqueado": "categoria"}, efetiva=False))
    assert avaliar(a, casos.caso("C04"))["ferramentas_proibidas"].ok


def test_resposta_sem_o_que_o_caso_exige_e_reprovada():
    a = _atendimento_sintetico(resposta="Tudo certo.", status="concluido")
    assert "resposta_contem_no_ultimo" in reprovados(a, casos.caso("C13"))
    b = _atendimento_sintetico(resposta="Pode me informar o número do pedido?", status="concluido")
    assert "resposta_contem_no_ultimo" not in reprovados(b, casos.caso("C13"))


@pytest.mark.parametrize("caso", GOLDEN_AVALIADOS)
def test_golden_roteirizado(versao, caso):
    requer(versao, "ferramentas")
    a = atender(versao, caso, roteiro=roteiro_golden(versao, caso))
    assert a.erro is None, a.erro
    assert reprovados(a, casos.caso(caso)) == {}
