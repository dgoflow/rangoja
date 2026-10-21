"""Contexto de uma execução: modo, roteiro/gravação ativos e o que foi usado (para os spans)."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from .. import config


@dataclass
class Contexto:
    modo: str = field(default_factory=config.modo)
    roteiro: Any = None          # Roteiro | None (import tardio evita ciclo)
    gravacao: Any = None         # Roteiro | None
    temperatura: float | None = None
    fontes: list[str] = field(default_factory=list)
    modelos: list[str] = field(default_factory=list)
    tentativas: list[int] = field(default_factory=list)
    respostas: list[tuple[str, Any]] = field(default_factory=list)  # (agente, LlmResponse), para gravar


_atual: ContextVar[Contexto] = ContextVar("rangoja_contexto")


def atual() -> Contexto:
    try:
        return _atual.get()
    except LookupError:
        ctx = Contexto()
        _atual.set(ctx)
        return ctx


def definir(ctx: Contexto) -> None:
    _atual.set(ctx)


def para_gravacao(ctx: Contexto, **metadados: Any) -> dict[str, Any] | None:
    """Converte as respostas desta execução no formato de gravação nomeada (lido por Roteiro.de_arquivo).

    Devolve None se alguma resposta tiver uma parte que não seja texto nem chamada de função."""
    por_agente: dict[str, list[dict[str, Any]]] = {}
    for agente, resposta in ctx.respostas:
        partes = resposta.content.parts if resposta.content and resposta.content.parts else []
        itens = []
        for parte in partes:
            if parte.function_call:
                fc = parte.function_call
                if fc.name == "set_model_response":
                    itens.append({"estruturada": dict(fc.args or {})})
                else:
                    itens.append({"chamada": fc.name, "args": dict(fc.args or {})})
            elif parte.text:
                itens.append({"texto": parte.text})
            else:
                return None
        if not itens:
            return None
        por_agente.setdefault(agente, []).append(itens[0] if len(itens) == 1 else {"partes": itens})
    return {**metadados, "respostas": por_agente}
