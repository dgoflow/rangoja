"""Resiliência (NB03, N4.4): falhas injetadas. Padrão esperado: v2 falha; v3 passa."""
from __future__ import annotations

from rangoja import falhas
from rangoja.armazem import Armazem
from rangoja.execucao import atender
from rangoja.modelo.roteiro import chamada
from rangoja.trajetoria import contar_chamadas

from cenarios import atendimento, decisao, montar_roteiro, requer, triagem


def _total(pedido_id: str) -> float:
    return sum(float(r["valor"]) for r in Armazem.atual().linhas("reembolsos", pedido_id=pedido_id)
               if r["origem"] == "sistema")


def test_ferramenta_fora_do_ar_escala(versao):
    requer(versao, "ferramentas")
    passos = atendimento(
        versao,
        triagem_passo=triagem("atraso", "5310"),
        principal=[
            chamada("buscar_pedido", pedido_id="5310"),
            chamada("escalar_para_humano", motivo="sistema indisponível", resumo="atraso 5310"),
            decisao("atraso", "escalar_para_humano", pedido_id="5310"),
        ],
    )
    with falhas.injetar("ferramenta_fora", alvo="buscar_pedido"):
        a = atender(versao, "C02", roteiro=montar_roteiro(passos))
    assert a.erro is None, a.erro
    assert a.status == "escalado"


def test_429_transitorio_e_repetido(versao):
    requer(versao, "ferramentas")
    passos = atendimento(
        versao,
        triagem_passo=triagem("atraso", "5310"),
        principal=[
            chamada("buscar_pedido", pedido_id="5310"),
            chamada("oferecer_cupom", pedido_id="5310", valor=10.0, motivo="atraso"),
            decisao("atraso", "voucher", pedido_id="5310", valor=10.0),
        ],
        resposta="Oferecemos um cupom de R$ 10 pelo atraso.",
    )
    with falhas.injetar("modelo_429", vezes=2):
        a = atender(versao, "C02", roteiro=montar_roteiro(passos))
    assert a.erro is None, a.erro
    assert a.status == "concluido"
    assert 3 in a.tentativas


def test_modelo_primario_fora_usa_o_secundario(versao):
    requer(versao, "ferramentas")
    passos = atendimento(
        versao,
        triagem_passo=triagem("atraso", "5310"),
        principal=[decisao("atraso", "nenhuma", pedido_id="5310")],
        resposta="Sem compensação para este atraso.",
    )
    with falhas.injetar("modelo_fora"):
        a = atender(versao, "C02", roteiro=montar_roteiro(passos))
    assert a.erro is None, a.erro
    assert "secundario" in a.modelos_usados


def test_resultado_ambiguo_nao_gera_loop(versao):
    requer(versao, "ferramentas")
    chamadas_buscar = [chamada("buscar_pedido", pedido_id="4821") for _ in range(4)]
    passos = atendimento(
        versao,
        triagem_passo=triagem("item_faltando", "4821"),
        principal=chamadas_buscar + [
            chamada("escalar_para_humano", motivo="resultado inconsistente", resumo="4821"),
            decisao("item_faltando", "escalar_para_humano", pedido_id="4821"),
        ],
    )
    with falhas.injetar("resultado_ambiguo", alvo="buscar_pedido"):
        a = atender(versao, "C01", roteiro=montar_roteiro(passos))
    assert contar_chamadas(a.trajetoria, "buscar_pedido") <= 3


def test_reembolso_em_dobro_por_timeout_apos_efeito(versao):
    requer(versao, "ferramentas")
    passos = atendimento(
        versao,
        triagem_passo=triagem("cobranca", "6002"),
        principal=[
            chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
            chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
            decisao("cobranca", "reembolso", pedido_id="6002", valor=42.9),
        ],
        resposta="Seu reembolso de R$ 42,90 foi registrado.",
    )
    with falhas.injetar("timeout_apos_efeito", alvo="registrar_reembolso"):
        a = atender(versao, "C03", roteiro=montar_roteiro(passos))
    assert a.erro is None, a.erro
    assert _total("6002") == 42.9


def test_conversa_sobrevive_a_reinicio_do_runner(versao):
    requer(versao, "ferramentas")
    from rangoja.execucao import aprovar, estado_persistido, reiniciar_runner
    passos = atendimento(
        versao,
        triagem_passo=triagem("item_faltando", "9001"),
        principal=[
            chamada("registrar_reembolso", pedido_id="9001", valor=120.0, motivo="item_faltando"),
            decisao("item_faltando", "reembolso", pedido_id="9001", valor=120.0),
        ],
    )
    a = atender(versao, "C09", roteiro=montar_roteiro(passos))
    assert a.status == "aguardando_aprovacao"
    reiniciar_runner(a)
    assert estado_persistido(a) is not None
    b = aprovar(a)
    assert b.status == "concluido"
    assert _total("9001") == 120.0
