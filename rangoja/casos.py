"""Casos canônicos (dados/casos.yaml). Valida o catálogo na primeira carga."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from . import dados


class Caso(BaseModel):
    id: str
    cliente_id: str
    pedido_id: str | None = None
    atendimentos: list[list[str]]
    esperado: dict[str, Any] = Field(default_factory=dict)
    usado_em: list[str] = Field(default_factory=list)
    origem: str | None = None
    transformacao: str | None = None
    relacao: str | None = None


@lru_cache(maxsize=1)
def _todos() -> dict[str, Caso]:
    brutos = dados.casos_brutos()
    por_id: dict[str, dict[str, Any]] = {b["id"]: b for b in brutos}
    if len(por_id) != len(brutos):
        raise ValueError("casos.yaml tem IDs duplicados")
    saida: dict[str, Caso] = {}
    for b in brutos:
        esperado = dict(b.get("esperado", {}))
        if "herda" in esperado:
            base = por_id[esperado.pop("herda")]["esperado"]
            esperado = {**base, **esperado}
        atendimentos = [a["mensagens"] for a in b["atendimentos"]]
        dados_caso = {**b, "atendimentos": atendimentos, "esperado": esperado}
        dados_caso.setdefault("usado_em", [])
        caso = Caso.model_validate(dados_caso)
        if dados.cliente(caso.cliente_id) is None:
            raise ValueError(f"{caso.id}: cliente {caso.cliente_id} inexistente")
        if caso.pedido_id and dados.pedido(caso.pedido_id) is None:
            raise ValueError(f"{caso.id}: pedido {caso.pedido_id} inexistente")
        saida[caso.id] = caso
    return saida


def caso(identificador: str) -> Caso:
    return _todos()[identificador]


def todos() -> list[Caso]:
    return list(_todos().values())
