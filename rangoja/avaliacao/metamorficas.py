"""Relações metamórficas: sem saber a resposta certa, sabemos como duas respostas se relacionam.

- invariância: entradas equivalentes (gíria, digitação, ordem, ruído) têm a mesma decisão;
- monotonicidade: mais atraso nunca reduz a compensação efetiva.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..execucao import Atendimento
from .programaticos import compensacao_efetiva


@dataclass(frozen=True)
class Violacao:
    relacao: str
    caso: str
    detalhe: str


@dataclass(frozen=True)
class Relacao:
    nome: str
    tipo: str                      # invariancia | monotonicidade
    casos: tuple[str, ...]         # origem primeiro, para invariância; em ordem crescente de atraso, para monotonicidade

    def verificar(self, resultados: dict[str, Atendimento]) -> list[Violacao]:
        if self.tipo == "invariancia":
            return self._invariancia(resultados)
        if self.tipo == "monotonicidade":
            return self._monotonicidade(resultados)
        raise ValueError(self.tipo)

    def _invariancia(self, resultados: dict[str, Atendimento]) -> list[Violacao]:
        origem = resultados[self.casos[0]]
        ref = _assinatura(origem)
        saida = []
        for caso in self.casos[1:]:
            atual = _assinatura(resultados[caso])
            if atual != ref:
                saida.append(Violacao(self.nome, caso, f"{atual} difere de {ref} (origem {self.casos[0]})"))
        return saida

    def _monotonicidade(self, resultados: dict[str, Atendimento]) -> list[Violacao]:
        saida = []
        anterior: Decimal | None = None
        anterior_caso = None
        for caso in self.casos:
            atual = compensacao_efetiva(resultados[caso])
            if anterior is not None and atual < anterior:
                saida.append(Violacao(self.nome, caso, f"compensação {atual} menor que {anterior} em {anterior_caso}"))
            anterior, anterior_caso = atual, caso
        return saida


def _assinatura(a: Atendimento) -> tuple:
    if a.decisao is None:
        return ("sem decisão", a.status)
    valor = None if a.decisao.valor is None else round(float(a.decisao.valor), 2)
    return (a.decisao.categoria, a.decisao.solucao, valor)


RELACOES: tuple[Relacao, ...] = (
    Relacao("invariancia_da_reclamacao_c01", "invariancia",
            ("C01", "C01-giria", "C01-digitacao", "C01-ordem", "C01-ruido")),
    Relacao("monotonicidade_do_atraso", "monotonicidade", ("C02-40", "C02-70", "C02-120")),
)
