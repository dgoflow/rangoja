"""Regras da política em código. Usadas por callbacks, ferramentas e testes.

O texto da política (dados/politica_reembolso.md) é a versão lida pelo modelo; um teste
garante que os números aqui aparecem lá.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .tipos import Categoria, Pedido, ReembolsoHistorico

LIMITE_AUTOMATICO = Decimal("50")
PRAZO_APROVACAO = timedelta(hours=24)
RECORRENCIA_MAX = 3
RECORRENCIA_JANELA = timedelta(days=30)
CUPOM_MAX = Decimal("15")
VOUCHER_ATRASO = Decimal("10")
ATRASO_VOUCHER_MIN = 40
ATRASO_REEMBOLSO_TAXA_MIN = 90

PRECEDENCIA: list[Categoria] = [
    "golpe", "cobranca", "item_faltando", "item_errado", "atraso", "qualidade",
]

CAMPOS_PREFERENCIA = {"local_entrega", "canal_contato", "horario_preferido"}

SOLUCOES: dict[str, list[str]] = {
    "item_faltando": ["reembolso", "escalar_para_humano"],
    "item_errado": ["reembolso", "reenvio", "escalar_para_humano"],
    "cobranca": ["reembolso", "escalar_para_humano"],
    "atraso": ["voucher", "voucher_e_reembolso_taxa", "nenhuma", "escalar_para_humano"],
    "qualidade": ["voucher", "escalar_para_humano"],
    "golpe": ["encaminhar_seguranca"],
    "fora_do_escopo": ["nenhuma"],
    "indefinida": ["pedir_informacao", "escalar_para_humano", "nenhuma"],
}

FERRAMENTAS_BASE = {"buscar_pedido", "consultar_politica", "escalar_para_humano"}
FERRAMENTAS_POR_CATEGORIA: dict[str, set[str]] = {
    "item_faltando": {"registrar_reembolso"},
    "item_errado": {"registrar_reembolso", "solicitar_reenvio"},
    "cobranca": {"registrar_reembolso"},
    "atraso": {"oferecer_cupom", "registrar_reembolso"},
    "qualidade": {"oferecer_cupom"},
    "golpe": {"encaminhar_seguranca"},
    "fora_do_escopo": set(),
    "indefinida": set(),
}


def categoria_principal(problemas: list[Categoria]) -> Categoria:
    for categoria in PRECEDENCIA:
        if categoria in problemas:
            return categoria
    return problemas[0] if problemas else "indefinida"


def solucoes_permitidas(categoria: str) -> list[str]:
    return list(SOLUCOES.get(categoria, SOLUCOES["indefinida"]))


def ferramentas_permitidas(categoria: str) -> set[str]:
    return set(FERRAMENTAS_BASE) | set(FERRAMENTAS_POR_CATEGORIA.get(categoria, set()))


def atraso_minutos(pedido: Pedido) -> int:
    entregue = pedido.horarios.entregue or pedido.horarios.prometido
    return int((entregue - pedido.horarios.prometido).total_seconds() // 60)


def compensacao_atraso(pedido: Pedido) -> tuple[str, Decimal]:
    """Compensação total por atraso. Monotônica no atraso (exigido pela relação de N4.7)."""
    minutos = atraso_minutos(pedido)
    if minutos >= ATRASO_REEMBOLSO_TAXA_MIN:
        return "voucher_e_reembolso_taxa", VOUCHER_ATRASO + pedido.taxa_entrega
    if minutos >= ATRASO_VOUCHER_MIN:
        return "voucher", VOUCHER_ATRASO
    return "nenhuma", Decimal("0")


def precisa_aprovacao(valor: float | Decimal) -> bool:
    return Decimal(str(valor)) > LIMITE_AUTOMATICO


def reembolsos_na_janela(reembolsos: list[ReembolsoHistorico], agora: datetime) -> int:
    return sum(1 for r in reembolsos if agora - RECORRENCIA_JANELA <= r.quando <= agora)


def cliente_recorrente(reembolsos: list[ReembolsoHistorico], agora: datetime) -> bool:
    return reembolsos_na_janela(reembolsos, agora) >= RECORRENCIA_MAX
