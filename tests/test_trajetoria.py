"""Trajetória (N4.5): ordem e ferramentas, roteirizadas. A estabilidade real é um teste `live`."""
from __future__ import annotations

import pytest

from rangoja import casos, config
from rangoja.avaliacao.programaticos import ferramentas_obrigatorias, ordem_obrigatoria
from rangoja.execucao import atender
from rangoja.modelo.roteiro import chamada

from cenarios import atendimento, decisao, montar_roteiro, requer, triagem
from cenarios_golden import roteiro_golden


@pytest.mark.parametrize("caso", ["C01", "C02-120", "C03", "C09"])
def test_trajetoria_do_roteiro_cumpre_ordem_e_ferramentas(versao, caso):
    requer(versao, "ferramentas")
    a = atender(versao, caso, roteiro=roteiro_golden(versao, caso))
    c = casos.caso(caso)
    assert ferramentas_obrigatorias(a, c).ok
    assert ordem_obrigatoria(a, c).ok


def test_desvio_de_fluxo_registrar_sem_consultar(versao):
    """O modelo tenta reembolsar sem consultar o pedido. Com a sequência, a consulta é feita em
    código antes de o modelo agir, então o desvio não ocorre; sem ela, a avaliação tem que pegar."""
    requer(versao, "ferramentas")
    passos = atendimento(
        versao,
        triagem_passo=triagem("cobranca", "6002"),
        principal=[
            chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
            decisao("cobranca", "reembolso", pedido_id="6002", valor=42.9),
        ],
    )
    a = atender(versao, "C03", roteiro=montar_roteiro(passos))
    resultado = ordem_obrigatoria(a, casos.caso("C03"))
    if "sequencia" in versao:
        assert resultado.ok, resultado.motivo
    else:
        assert not resultado.ok


@pytest.mark.live
def test_estabilidade_da_trajetoria_com_modelo_real(versao):
    """Repete cada caso N vezes com o modelo real e exige taxa mínima de trajetórias corretas."""
    requer(versao, "ferramentas")
    caso = casos.caso("C01")
    corretas = 0
    for _ in range(config.repeticoes()):
        a = atender(versao, caso)
        corretas += ferramentas_obrigatorias(a, caso).ok and ordem_obrigatoria(a, caso).ok
    taxa = corretas / config.repeticoes()
    assert taxa >= config.limiar_estabilidade(), f"estabilidade {taxa:.2f} abaixo do limiar"
