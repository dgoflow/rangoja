"""Relações metamórficas (N4.7). Sem saber a resposta certa, testamos como respostas se relacionam.

Os testes sem `live` usam roteiros escritos à mão e verificam o detector: uma relação violada
tem que ser pega, e uma relação respeitada não pode gerar falso alarme. O teste `live` mede o
modelo real (requer RANGOJA_MODO=live e chave de API).
"""
from __future__ import annotations

import pytest

from rangoja.avaliacao.metamorficas import Relacao, RELACOES
from rangoja.execucao import atender

from cenarios import atendimento, decisao, montar_roteiro, requer, triagem
from cenarios_golden import roteiro_golden

INVARIANCIA = next(r for r in RELACOES if r.tipo == "invariancia")
MONOTONICIDADE = next(r for r in RELACOES if r.tipo == "monotonicidade")


def _roteiro_c01_variantes(versao, decisao_variante: dict | None = None) -> dict:
    """Roteiro de todo o grupo C01: a mesma decisão para as variantes, salvo `decisao_variante`."""
    partes = [roteiro_golden(versao, "C01")]
    for variante in INVARIANCIA.casos[1:]:
        partes.append(roteiro_golden(versao, "C01") if decisao_variante is None or variante not in decisao_variante
                      else decisao_variante[variante])
    return partes


def _rodar_grupo(versao, casos_roteiros: dict[str, dict]) -> dict:
    return {caso: atender(versao, caso, roteiro=roteiro) for caso, roteiro in casos_roteiros.items()}


def test_invariancia_com_modelo_consistente_nao_gera_alarme(versao):
    requer(versao, "ferramentas")
    roteiros = {c: roteiro_golden(versao, "C01") for c in INVARIANCIA.casos}
    resultados = _rodar_grupo(versao, roteiros)
    assert INVARIANCIA.verificar(resultados) == []


def test_invariancia_pega_modelo_que_decide_diferente_para_gíria(versao):
    requer(versao, "ferramentas")
    roteiros = {c: roteiro_golden(versao, "C01") for c in INVARIANCIA.casos}
    roteiros["C01-giria"] = montar_roteiro(atendimento(
        versao,
        triagem_passo=triagem("item_faltando", "4821"),
        principal=[decisao("item_faltando", "escalar_para_humano", pedido_id="4821")],
    ))
    resultados = _rodar_grupo(versao, roteiros)
    violacoes = INVARIANCIA.verificar(resultados)
    assert [v.caso for v in violacoes] == ["C01-giria"]


def test_monotonicidade_com_compensacao_crescente_nao_gera_alarme(versao):
    requer(versao, "ferramentas")
    roteiros = {c: roteiro_golden(versao, c) for c in MONOTONICIDADE.casos}
    assert MONOTONICIDADE.verificar(_rodar_grupo(versao, roteiros)) == []


def test_monotonicidade_pega_atraso_maior_com_compensacao_menor(versao):
    requer(versao, "ferramentas")
    roteiros = {c: roteiro_golden(versao, c) for c in MONOTONICIDADE.casos}
    # 70 min: o modelo diz "voucher" mas não oferece nada (sem chamada de cupom)
    roteiros["C02-70"] = montar_roteiro(atendimento(
        versao,
        triagem_passo=triagem("atraso", "5310"),
        principal=[decisao("atraso", "voucher", pedido_id="5310", valor=10.0)],
    ))
    roteiros["C02-40"] = roteiro_golden(versao, "C02-40")
    roteiros["C02-120"] = roteiro_golden(versao, "C02-120")
    violacoes = MONOTONICIDADE.verificar(_rodar_grupo(versao, roteiros))
    assert [v.caso for v in violacoes] == ["C02-70"]


def test_relacao_declara_tipo_valido():
    with pytest.raises(ValueError):
        Relacao("x", "desconhecida", ("C01",)).verificar({"C01": None})


@pytest.mark.live
def test_relacoes_com_modelo_real(versao):
    """Mede o modelo real: nenhuma violação de invariância ou monotonicidade nos casos do grupo."""
    requer(versao, "ferramentas")
    resultados = _rodar_grupo(versao, {c: None for c in INVARIANCIA.casos})  # atender sem roteiro
    assert INVARIANCIA.verificar(resultados) == []
