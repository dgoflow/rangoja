"""Estado mutável do "sistema da empresa" (SQLite), separado da sessão do agente.

Uma instância por seção. Em testes, um banco em memória por teste (`reset`).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import dados, relogio

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reembolsos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id TEXT NOT NULL, cliente_id TEXT NOT NULL, valor TEXT NOT NULL,
  motivo TEXT NOT NULL, chave TEXT UNIQUE, quando TEXT NOT NULL, origem TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id TEXT, cliente_id TEXT,
  valor TEXT NOT NULL, motivo TEXT, quando TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reenvios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id TEXT, item TEXT, quando TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id TEXT, motivo TEXT, resumo TEXT, quando TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seguranca (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id TEXT, cliente_id TEXT, relato TEXT, quando TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pendencias (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sessao_id TEXT NOT NULL, cliente_id TEXT NOT NULL,
  chamada_id TEXT NOT NULL, ferramenta TEXT NOT NULL, args_json TEXT NOT NULL,
  criada_em TEXT NOT NULL, resolvida_em TEXT, resolucao TEXT
);
"""

_atual: "Armazem | None" = None


class Armazem:
    def __init__(self, caminho: str | Path = ":memory:") -> None:
        self.con = sqlite3.connect(str(caminho), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(_SCHEMA)

    @classmethod
    def reset(cls, caminho: str | Path = ":memory:", semear: bool = True) -> "Armazem":
        global _atual
        if _atual is not None:
            _atual.con.close()
        _atual = cls(caminho)
        if semear:
            _atual.semear_clientes()
        return _atual

    @classmethod
    def atual(cls) -> "Armazem":
        global _atual
        if _atual is None:
            cls.reset()
        assert _atual is not None
        return _atual

    def semear_clientes(self) -> None:
        """Histórico de reembolsos de clientes.json entra no sistema como fato, origem 'semente'."""
        for cliente in dados.clientes():
            for r in cliente.reembolsos:
                self.con.execute(
                    "INSERT INTO reembolsos (pedido_id, cliente_id, valor, motivo, chave, quando, origem)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (r.pedido_id, cliente.cliente_id, str(r.valor), "semente", None, r.quando.isoformat(), "semente"),
                )
        self.con.commit()

    def inserir(self, tabela: str, **campos: Any) -> int:
        colunas = ", ".join(campos)
        marcas = ", ".join("?" for _ in campos)
        cur = self.con.execute(f"INSERT INTO {tabela} ({colunas}) VALUES ({marcas})", tuple(campos.values()))
        self.con.commit()
        return int(cur.lastrowid)

    def linhas(self, tabela: str, **filtros: Any) -> list[dict[str, Any]]:
        where = " AND ".join(f"{k} = ?" for k in filtros) or "1=1"
        cur = self.con.execute(f"SELECT * FROM {tabela} WHERE {where} ORDER BY id", tuple(filtros.values()))
        return [dict(r) for r in cur.fetchall()]

    def reembolso_por_chave(self, chave: str) -> dict[str, Any] | None:
        linhas = self.linhas("reembolsos", chave=chave)
        return linhas[0] if linhas else None

    def reembolsos_do_cliente(self, cliente_id: str, agora: datetime | None = None, dias: int = 30) -> list[dict[str, Any]]:
        agora = agora or relogio.agora()
        from datetime import timedelta
        inicio = agora - timedelta(days=dias)
        return [
            r for r in self.linhas("reembolsos", cliente_id=cliente_id)
            if inicio <= datetime.fromisoformat(r["quando"]) <= agora
        ]

    def total_reembolsado(self, pedido_id: str | None = None) -> Decimal:
        linhas = self.linhas("reembolsos", pedido_id=pedido_id) if pedido_id else self.linhas("reembolsos")
        return sum((Decimal(r["valor"]) for r in linhas if r["origem"] != "semente"), Decimal("0"))
