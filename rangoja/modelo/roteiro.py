"""Roteiros: respostas escritas à mão, consumidas em ordem por agente.

Usados para falhas induzidas (NB02, NB03) e para testes de orquestração: o roteiro simula
o modelo, inclusive tentando o que não deve, e o sistema precisa barrar.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from google.genai import types
from google.adk.models.llm_response import LlmResponse

_ids = itertools.count(1)


class RoteiroEsgotado(Exception):
    """O agente pediu mais respostas do que o roteiro previu."""


@dataclass(frozen=True)
class Passo:
    tipo: str  # texto | chamada | estruturada | funcao
    dados: Any = None


def texto(conteudo: str) -> Passo:
    return Passo("texto", conteudo)


def chamada(ferramenta: str, **args: Any) -> Passo:
    return Passo("chamada", (ferramenta, args))


def estruturada(**campos: Any) -> Passo:
    """Saída estruturada. Com ferramentas, o ADK a entrega por `set_model_response`; sem, como texto JSON."""
    return Passo("estruturada", campos)


def varias(*passos: Passo) -> Passo:
    """Uma resposta com várias partes (ex.: chamadas de ferramenta em paralelo)."""
    return Passo("varias", passos)


def funcao(fn: Callable[[Any], Passo]) -> Passo:
    """Passo calculado a partir da requisição (ex.: ecoar o último resultado de ferramenta)."""
    return Passo("funcao", fn)


@dataclass
class Roteiro:
    passos: dict[str, list[Passo]] = field(default_factory=dict)
    _cursor: dict[str, int] = field(default_factory=dict)

    def proximo(self, agente: str, requisicao: Any) -> Passo | None:
        """Próximo passo do agente, ou None se o roteiro não cobre esse agente."""
        if agente not in self.passos:
            return None
        i = self._cursor.get(agente, 0)
        lista = self.passos[agente]
        if i >= len(lista):
            raise RoteiroEsgotado(f"roteiro do agente '{agente}' esgotado após {i} respostas")
        self._cursor[agente] = i + 1
        passo = lista[i]
        if passo.tipo == "funcao":
            passo = passo.dados(requisicao)
        return passo

    @classmethod
    def de_arquivo(cls, caminho: Path) -> "Roteiro":
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        passos: dict[str, list[Passo]] = {}
        for agente, lista in bruto["respostas"].items():
            passos[agente] = [_de_json(item) for item in lista]
        return cls(passos)


def _de_json(item: dict[str, Any]) -> Passo:
    if "partes" in item:
        return varias(*[_de_json(i) for i in item["partes"]])
    if "texto" in item:
        return texto(item["texto"])
    if "chamada" in item:
        return chamada(item["chamada"], **item.get("args", {}))
    return estruturada(**item["estruturada"])


def _parte_chamada(nome: str, args: dict[str, Any]) -> types.Part:
    return types.Part(function_call=types.FunctionCall(id=f"rangoja_{next(_ids)}", name=nome, args=args))


def _partes(passo: Passo, requisicao: Any) -> list[types.Part]:
    if passo.tipo == "texto":
        return [types.Part(text=passo.dados)]
    if passo.tipo == "chamada":
        nome, args = passo.dados
        return [_parte_chamada(nome, args)]
    if passo.tipo == "estruturada":
        if "set_model_response" in getattr(requisicao, "tools_dict", {}):
            return [_parte_chamada("set_model_response", passo.dados)]
        return [types.Part(text=json.dumps(passo.dados, ensure_ascii=False, default=str))]
    if passo.tipo == "varias":
        return [p for sub in passo.dados for p in _partes(sub, requisicao)]
    raise ValueError(f"passo desconhecido: {passo.tipo}")


def para_resposta(passo: Passo, requisicao: Any) -> LlmResponse:
    """Converte um passo em LlmResponse. Saída estruturada respeita a forma que o ADK espera."""
    return LlmResponse(content=types.Content(role="model", parts=_partes(passo, requisicao)))
