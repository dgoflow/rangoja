"""Registro das seções dos notebooks: caso, versões de falha e correção, gravações e roteiro.

Correções são cumulativas: a correção da seção k é a da seção k-1 mais um componente.
Gravação = cadeia de respostas reais do modelo (rangoja/gravacoes/); roteiro = resposta escrita à mão.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .versoes import Versao, montar, v0, v1, v2, v3

# ---- NB01: v0 -> v1
N12 = montar(v0, com=["ferramentas"])
N14 = N12.com("schema")
N15F = v1.sem("estado", "contexto_enxuto", "memoria_livre")
N15C = v1.sem("contexto_enxuto", "memoria_livre")
N16C = v1.sem("memoria_livre")

# ---- NB02: v1 -> v2
N21 = montar(v1, com=["aprovacao"])
N22 = N21.com("guardrail_entrada")
N23 = N22.com("guardrail_saida")
N24 = N23.com("memoria_segura")      # troca memoria_livre por memoria_segura
N25 = N24.com("sequencia")
N26 = N25.com("categorias")
N27 = v2                             # N26 + contrato

# ---- NB03: v2 -> v3
N32 = v2.com("erros_estruturados")
N33 = N32.com("retry", "fallback")
N34 = N33.com("limites")
N35 = N34.com("persistencia")
N36 = v3                             # N35 + idempotencia


@dataclass(frozen=True)
class SpecSecao:
    id: str
    caso: str | None
    falha: Versao | None
    correcao: Versao | None
    gravacoes: dict[str, str] = field(default_factory=dict)   # rótulo -> nome da gravação
    casos_extra: dict[str, str] = field(default_factory=dict)  # rótulo -> outro caso da seção
    roteiro: str | None = None                                  # chave em roteiros.ROTEIROS


SECOES: dict[str, SpecSecao] = {s.id: s for s in [
    SpecSecao("N1.1", "C01", v0, None, {"falha": "N1.1/falha"}),
    SpecSecao("N1.2", "C01", v0, N12, {"falha": "N1.1/falha", "correcao": "N1.2/correcao"}),
    SpecSecao("N1.3", "C01", None, N12, {"correcao": "N1.2/correcao"}),
    SpecSecao("N1.4", "C02", N12, N14, {"falha": "N1.4/falha", "correcao": "N1.4/correcao"}),
    SpecSecao("N1.5", "C11", N15F, N15C, {"falha": "N1.5/falha", "correcao": "N1.5/correcao"}),
    SpecSecao("N1.6", "C01", N15C, N16C, {"falha": "N1.6/falha", "correcao": "N1.6/correcao"}),
    SpecSecao("N1.7", "C13", N16C, v1, {"falha": "N1.7/falha", "correcao": "N1.7/correcao"}),
    SpecSecao("N2.1", "C09", v1, N21, {"falha": "N2.1/C09", "correcao": "N2.1/correcao"}),
    SpecSecao("N2.2", "C05", N21, N22, {"falha": "N2.2/falha", "correcao": "N2.2/correcao",
                                         "c10": "N2.2/correcao_c10"}, {"c10": "C10"}),
    SpecSecao("N2.3", "C12", N22, N23, roteiro="N2.3"),
    SpecSecao("N2.4", "C07", N23, N24,
              {"falha": "N2.4/C07", "correcao": "N2.4/correcao_c07",
               "falha_c08": "N2.4/C08", "correcao_c08": "N2.4/correcao_c08"}, {"c08": "C08"}),
    SpecSecao("N2.5", "C03", N24, N25, roteiro="N2.5"),
    SpecSecao("N2.6", "C04", N25, N26, {"v1_gravada": "N2.6/C04"}, roteiro="N2.6"),
    SpecSecao("N2.7", "C06", N26, N27, roteiro="N2.7"),
    SpecSecao("N3.0", "C01", None, v2, roteiro="N3.0"),
    SpecSecao("N3.1", "C03", N24, v2, roteiro="N3.1"),
    SpecSecao("N3.2", "C03", v2, N32, roteiro="N3.2"),
    SpecSecao("N3.3", "C02", N32, N33, roteiro="N3.3"),
    SpecSecao("N3.4", "C01", N33, N34, roteiro="N3.4"),
    SpecSecao("N3.5", "C09", N34, N35, roteiro="N3.5"),
    SpecSecao("N3.6", "C03", N35, N36, roteiro="N3.6"),
    # extras (notebooks/extras/): independentes dos principais
    SpecSecao("X1.1", "C01", None, v2, roteiro="N3.0"),
    SpecSecao("X1.2", "C08", None, N24, {"correcao": "N2.4/correcao_c08"}),
    SpecSecao("X2.1", "C11", None, N15C, {"correcao": "N1.5/correcao"}),
    SpecSecao("X3.1", None, None, None),
]}

# (seção, nome, versão, caso, critério): execuções a gravar com o modelo real (scripts/gravar_secoes.py).
# Com critério, o script tenta até 6 vezes, guarda a primeira que o satisfaz e registra a taxa no
# arquivo (`amostra`): é um exemplo representativo da lição, não a única execução possível.
# As falhas de N2.1, N2.4 e N2.6 vêm da rodada exploratória (gravacoes/N2.x/Cxx.json).
GRAVAR: list[tuple[str, str, Versao, str, str | None]] = [
    ("N1.1", "falha", v0, "C01", None),
    ("N1.2", "correcao", N12, "C01", "consultou"),
    ("N1.4", "falha", N12, "C02", None), ("N1.4", "correcao", N14, "C02", None),
    ("N1.5", "falha", N15F, "C11", None), ("N1.5", "correcao", N15C, "C11", "consulta_unica"),
    ("N1.6", "falha", N15C, "C01", "consultou"), ("N1.6", "correcao", N16C, "C01", "consultou"),
    ("N1.7", "falha", N16C, "C13", "sem_portaria"), ("N1.7", "correcao", v1, "C13", "menciona_portaria"),
    ("N2.1", "correcao", N21, "C09", None),
    ("N2.2", "falha", N21, "C05", None), ("N2.2", "correcao", N22, "C05", None),
    ("N2.2", "correcao_c10", N22, "C10", None),
    ("N2.4", "correcao_c07", N24, "C07", None), ("N2.4", "correcao_c08", N24, "C08", None),
]
