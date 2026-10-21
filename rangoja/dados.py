"""Leitura dos dados fictícios (somente leitura). O estado mutável fica em armazem.py."""
from __future__ import annotations

import json
from functools import lru_cache

import yaml

from . import config
from .tipos import Cliente, Entregador, Pedido


def _json(nome: str):
    return json.loads((config.DADOS / nome).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _pedidos() -> dict[str, Pedido]:
    return {p["pedido_id"]: Pedido.model_validate(p) for p in _json("pedidos.json")}


@lru_cache(maxsize=1)
def _clientes() -> dict[str, Cliente]:
    return {c["cliente_id"]: Cliente.model_validate(c) for c in _json("clientes.json")}


@lru_cache(maxsize=1)
def _entregadores() -> dict[str, Entregador]:
    return {k: Entregador.model_validate(v) for k, v in _json("entregadores.json").items()}


def pedido(pedido_id: str | None) -> Pedido | None:
    return _pedidos().get(pedido_id) if pedido_id else None


def cliente(cliente_id: str) -> Cliente | None:
    return _clientes().get(cliente_id)


def clientes() -> list[Cliente]:
    return list(_clientes().values())


def entregador(entregador_id: str) -> Entregador | None:
    return _entregadores().get(entregador_id)


def entregadores() -> list[Entregador]:
    return list(_entregadores().values())


@lru_cache(maxsize=1)
def politica_secoes() -> dict[str, str]:
    """Texto da política dividido por seção (`## tema`)."""
    texto = (config.DADOS / "politica_reembolso.md").read_text(encoding="utf-8")
    secoes: dict[str, str] = {}
    atual = None
    for linha in texto.splitlines():
        if linha.startswith("## "):
            atual = linha[3:].strip()
            secoes[atual] = ""
        elif atual is not None:
            secoes[atual] += linha + "\n"
    return {k: v.strip() for k, v in secoes.items()}


@lru_cache(maxsize=1)
def casos_brutos() -> list[dict]:
    return yaml.safe_load((config.DADOS / "casos.yaml").read_text(encoding="utf-8"))
