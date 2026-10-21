"""O catálogo de casos é válido e as relações metamórficas apontam para casos existentes."""
from __future__ import annotations

from rangoja import casos


def test_ids_unicos_e_validos():
    ids = [c.id for c in casos.todos()]
    assert len(ids) == len(set(ids))
    assert {"C01", "C09", "C11", "C13"} <= set(ids)


def test_variantes_herdam_o_esperado_da_origem():
    assert casos.caso("C01-giria").esperado["categoria"] == casos.caso("C01").esperado["categoria"]
    assert casos.caso("C01-giria").esperado["valor"] == casos.caso("C01").esperado["valor"]


def test_pedidos_de_monotonicidade_tem_atrasos_distintos():
    from rangoja import dados, politica
    minutos = [politica.atraso_minutos(dados.pedido(casos.caso(c).pedido_id)) for c in ("C02-40", "C02-70", "C02-120")]
    assert minutos == [40, 70, 120]
