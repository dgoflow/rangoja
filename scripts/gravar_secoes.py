"""Grava, com o modelo real, as execuções das seções dos notebooks (gravacoes/<seção>/<nome>.json).

Falhas de N2.1, N2.4 e N2.6 já vêm da rodada exploratória. Com critério (ver secoes.GRAVAR), tenta
até 6 vezes, guarda a primeira execução que o satisfaz e registra a taxa em `amostra`. Uso:
    .venv/bin/python scripts/gravar_secoes.py            # só o que falta
    .venv/bin/python scripts/gravar_secoes.py --forcar   # regrava tudo
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ambiente import exigir_modo_ao_vivo  # noqa: E402

exigir_modo_ao_vivo("record")

from rangoja import config  # noqa: E402
from rangoja.armazem import Armazem  # noqa: E402
from rangoja.execucao import atender  # noqa: E402
from rangoja.modelo import contexto, gravacao  # noqa: E402
from rangoja.secoes import GRAVAR  # noqa: E402
from rangoja.trajetoria import chamou, contar_chamadas  # noqa: E402

TENTATIVAS = 6

CRITERIOS = {
    "consulta_e_valor_real": lambda a: chamou(a.trajetoria, "buscar_pedido") and any(
        c.efetiva and c.ferramenta == "registrar_reembolso" and abs(Decimal(str(c.args.get("valor", 0))) - 8) < Decimal("0.01")
        for c in a.trajetoria),
    "consulta_repetida": lambda a: contar_chamadas(a.trajetoria, "buscar_pedido") >= 2,
    "consulta_unica": lambda a: a.erro is None and contar_chamadas(a.trajetoria, "buscar_pedido") == 1,
    "consultou": lambda a: a.erro is None and chamou(a.trajetoria, "buscar_pedido"),
    "sem_portaria": lambda a: a.erro is None and "portaria" not in (a.resposta or "").lower(),
    "menciona_portaria": lambda a: a.erro is None and "portaria" in (a.resposta or "").lower(),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--forcar", action="store_true")
    p.add_argument("--so", nargs="*", help="só estes, no formato N1.2/correcao")
    args = p.parse_args()
    for secao, nome, versao, caso, criterio in GRAVAR:
        if args.so and f"{secao}/{nome}" not in args.so:
            continue
        destino = config.GRAVACOES / f"{secao}/{nome}.json"
        if destino.exists() and not args.forcar:
            print(f"-- {secao}/{nome} já gravada")
            continue
        escolhida = None
        satisfizeram = 0
        n = TENTATIVAS if criterio else 1
        for _ in range(n):
            Armazem.reset()
            a = atender(versao, caso)
            ok = a.erro is None and (CRITERIOS[criterio](a) if criterio else True)
            if ok:
                satisfizeram += 1
                if escolhida is None:
                    escolhida = (a, list(contexto.atual().respostas))
        a, respostas = escolhida if escolhida else (a, list(contexto.atual().respostas))
        contexto.atual().respostas[:] = respostas
        amostra = {"criterio": criterio, "tentativas": n, "satisfizeram": satisfizeram} if criterio else None
        arquivo = gravacao.salvar(f"{secao}/{nome}", contexto.atual(), secao=secao, versao=versao.nome,
                                  caso=caso, amostra=amostra)
        marca = "OK " if arquivo and (escolhida or not criterio) else "!! "
        taxa = f" critério {criterio}: {satisfizeram}/{n}" if criterio else ""
        print(f"{marca}{secao}/{nome:<14} {versao.nome:<28} {caso:<4} status={a.status}{taxa}")


if __name__ == "__main__":
    main()
