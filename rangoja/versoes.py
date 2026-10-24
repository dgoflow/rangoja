"""Versões como montagens de componentes com dependências.

    v0 = {prompt}
    v1 = v0 + ferramentas, schema, estado, contexto_enxuto (substitui prompt), memoria_livre
    v2 = v1 - memoria_livre + memoria_segura, aprovacao, guardrails, sequencia, categorias, contrato
    v3 = v2 + erros_estruturados, retry, fallback, limites, persistencia, idempotencia

`montar(base, com=[], sem=[])` aplica as remoções (levando junto os dependentes) e depois as
inclusões (removendo o que cada uma substitui). Ver specs/pacote/03_componentes_versoes.md.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Iterable

from . import agentes

REQUER: dict[str, frozenset[str]] = {
    "prompt": frozenset(),
    "ferramentas": frozenset(),
    "schema": frozenset({"ferramentas"}),
    "estado": frozenset({"ferramentas"}),
    "contexto_enxuto": frozenset({"ferramentas"}),
    "memoria_livre": frozenset({"estado"}),
    "memoria_segura": frozenset({"estado"}),
    "aprovacao": frozenset({"ferramentas"}),
    "guardrail_entrada": frozenset(),
    "guardrail_saida": frozenset(),
    "sequencia": frozenset({"schema", "estado"}),
    "categorias": frozenset({"sequencia"}),
    "contrato": frozenset({"sequencia"}),
    "erros_estruturados": frozenset({"ferramentas"}),
    "retry": frozenset(),
    "fallback": frozenset({"retry"}),
    "limites": frozenset({"ferramentas"}),
    "persistencia": frozenset({"estado"}),
    "idempotencia": frozenset({"ferramentas"}),
}

SUBSTITUI: dict[str, frozenset[str]] = {
    "contexto_enxuto": frozenset({"prompt"}),
    "memoria_segura": frozenset({"memoria_livre"}),
}

ORDEM = list(REQUER)

# Nome semântico de cada versão: o prefixo vN mantém a ordem; o resto diz o que a versão é.
# O `nome` curto (v0, v1...) continua sendo a chave usada pela linha de comando, pelos testes e pelo CI.
APELIDOS = {"v0": "v0_so_prompt", "v1": "v1_agente", "v2": "v2_controlado", "v3": "v3_robusto"}
DESCRICAO_VERSAO = {
    "v0": "só o prompt, com a política colada. Sem ferramentas, sem decisão estruturada, sem estado.",
    "v1": "um agente: ferramentas, decisão estruturada, estado da conversa, contexto enxuto e memória do cliente.",
    "v2": "um agente controlado: aprovação humana, guardrails, memória segura, sequência, categorias e contrato entre etapas.",
    "v3": "um agente robusto: tudo da v2, mais erros estruturados, retry e fallback, limites, persistência e idempotência.",
}


class ComposicaoInvalida(ValueError):
    pass


def _dependentes(nome: str, conjunto: set[str]) -> set[str]:
    """Componentes que deixam de fazer sentido se `nome` sair."""
    return {c for c in conjunto if nome in REQUER.get(c, frozenset())}


def _fechar_remocao(conjunto: set[str], removidos: Iterable[str]) -> set[str]:
    pendentes = set(removidos) & conjunto
    removidos_total: set[str] = set()
    while pendentes:
        nome = pendentes.pop()
        if nome in removidos_total:
            continue
        removidos_total.add(nome)
        conjunto.discard(nome)
        pendentes |= _dependentes(nome, conjunto)
    return removidos_total


@dataclass(frozen=True)
class Versao:
    nome: str
    componentes: frozenset[str]

    def __contains__(self, componente: str) -> bool:
        return componente in self.componentes

    def sem(self, *removidos: str) -> "Versao":
        return montar(self, sem=removidos)

    def com(self, *adicionados: str) -> "Versao":
        return montar(self, com=adicionados)

    def construir(self) -> "agentes.Construida":
        return agentes.construir(self.componentes)

    @property
    def titulo(self) -> str:
        """Nome legível: 'v0+ferramentas' vira 'v0_so_prompt + ferramentas'."""
        achou = re.match(r"(v\d)(.*)$", self.nome)
        if not achou:
            return self.nome
        base, resto = achou.groups()
        return APELIDOS.get(base, base) + resto.replace("+", " + ").replace("-", " − ")

    def _componentes_na_ordem(self) -> list[str]:
        return sorted(self.componentes, key=ORDEM.index)

    def __repr__(self) -> str:
        from .notebook import DESCRICOES
        topo = self.titulo + (f": {DESCRICAO_VERSAO[self.nome]}" if self.nome in DESCRICAO_VERSAO else "")
        return "\n".join([topo, *[f"  {c}: {DESCRICOES.get(c, '')}" for c in self._componentes_na_ordem()]])

    def _repr_html_(self) -> str:
        from .notebook import DESCRICOES
        linhas = "".join(f"<tr><td><code>{c}</code></td><td>{html.escape(DESCRICOES.get(c, ''))}</td></tr>"
                         for c in self._componentes_na_ordem())
        resumo = DESCRICAO_VERSAO.get(self.nome, "montagem a partir de uma versão base, componente por componente.")
        return f"<div><b>{html.escape(self.titulo)}</b>: {html.escape(resumo)}</div><table>{linhas}</table>"


def montar(base: Versao | str, com: Iterable[str] = (), sem: Iterable[str] = (), nome: str | None = None) -> Versao:
    conjunto = set(base.componentes if isinstance(base, Versao) else base)
    nome_base = base.nome if isinstance(base, Versao) else "custom"
    removidos = _fechar_remocao(conjunto, sem)
    for c in com:
        if c not in REQUER:
            raise ComposicaoInvalida(f"componente desconhecido: {c}")
        conjunto -= SUBSTITUI.get(c, frozenset())
        conjunto.add(c)
    for c in conjunto:
        faltam = REQUER[c] - conjunto
        if faltam:
            raise ComposicaoInvalida(f"'{c}' exige {sorted(faltam)}")
    if nome is None:
        sufixos = [f"-{r}" for r in sorted(removidos)] + [f"+{a}" for a in com]
        nome = nome_base + "".join(sufixos)
    return Versao(nome, frozenset(conjunto))


v0 = Versao("v0", frozenset({"prompt"}))
v1 = montar(v0, com=["ferramentas", "schema", "estado", "contexto_enxuto", "memoria_livre"], nome="v1")
v2 = montar(
    v1,
    sem=["memoria_livre"],
    com=["aprovacao", "guardrail_entrada", "guardrail_saida", "memoria_segura",
         "sequencia", "categorias", "contrato"],
    nome="v2",
)
v3 = montar(
    v2,
    com=["erros_estruturados", "retry", "fallback", "limites", "persistencia", "idempotencia"],
    nome="v3",
)

VERSOES = {"v0": v0, "v1": v1, "v2": v2, "v3": v3}
v0_so_prompt, v1_agente, v2_controlado, v3_robusto = v0, v1, v2, v3


def resolver(nome: str) -> Versao:
    """`v2`, `v2-contrato`, `v1+aprovacao` ... Remoções com '-', inclusões com '+'."""
    for curto, apelido in APELIDOS.items():  # aceita também o nome semântico
        nome = nome.replace(apelido, curto)
    base, *resto = nome.replace("+", " +").replace("-", " -").split()
    versao = VERSOES[base]
    for item in resto:
        if item.startswith("-"):
            versao = versao.sem(item[1:])
        elif item.startswith("+"):
            versao = versao.com(item[1:])
    return versao
