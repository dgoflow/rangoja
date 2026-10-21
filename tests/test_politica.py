"""Regras de política: os números do código precisam estar no texto que o modelo lê."""
from __future__ import annotations

from decimal import Decimal

from rangoja import dados, politica
from rangoja.tipos import Pedido


def test_numeros_da_politica_aparecem_no_texto():
    texto = " ".join(dados.politica_secoes().values())
    assert "R$ 50" in texto
    assert "R$ 15" in texto
    assert "R$ 10" in texto
    assert "3 ou mais" in texto
    assert "24 horas" in texto


def test_precedencia_de_categoria():
    assert politica.categoria_principal(["atraso", "cobranca", "golpe"]) == "golpe"
    assert politica.categoria_principal(["qualidade", "item_faltando"]) == "item_faltando"
    assert politica.categoria_principal([]) == "indefinida"


def test_golpe_so_permite_encaminhar():
    assert politica.solucoes_permitidas("golpe") == ["encaminhar_seguranca"]
    assert "registrar_reembolso" not in politica.ferramentas_permitidas("golpe")


def test_compensacao_por_atraso_e_monotonica():
    pedidos = [dados.pedido(p) for p in ("5340", "5310", "5420")]  # 40, 70, 120 min
    valores = [politica.compensacao_atraso(p)[1] for p in pedidos]
    assert valores == sorted(valores)
    assert valores == [Decimal("10"), Decimal("10"), Decimal("17")]


def test_limite_automatico():
    assert not politica.precisa_aprovacao(50)
    assert politica.precisa_aprovacao(50.01)


def test_recorrencia_usa_a_janela_de_30_dias():
    from datetime import datetime, timedelta, timezone

    from rangoja.tipos import ReembolsoHistorico
    agora = datetime(2026, 11, 10, 12, tzinfo=timezone(timedelta(hours=-3)))
    antigos = [ReembolsoHistorico(pedido_id="x", valor=1, quando=agora - timedelta(days=45))] * 5
    recentes = [ReembolsoHistorico(pedido_id="x", valor=1, quando=agora - timedelta(days=d)) for d in (1, 2, 3)]
    assert not politica.cliente_recorrente(antigos, agora)
    assert politica.cliente_recorrente(recentes, agora)


def test_atraso_minutos_do_pedido_fixture():
    pedido: Pedido = dados.pedido("5310")
    assert politica.atraso_minutos(pedido) == 70
