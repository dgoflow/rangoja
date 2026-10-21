"""Grava atendimentos com o modelo real (RANGOJA_MODO=record).

Cada chamada ao modelo vai para o cache em .cache/modelo/. Além disso, cada caso gera um
relatório em rangoja/gravacoes/<versao>/<caso>.json com o que de fato aconteceu.

Uso (com OPENAI_API_KEY no .env):
    .venv/bin/python scripts/gravar.py --versao v3
    .venv/bin/python scripts/gravar.py --versao v1 --casos C04 C09
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ambiente import exigir_modo_ao_vivo  # noqa: E402

exigir_modo_ao_vivo("record")

from rangoja import casos, config  # noqa: E402
from rangoja.avaliacao.programaticos import reprovados  # noqa: E402
from rangoja.execucao import atender  # noqa: E402
from rangoja.versoes import resolver  # noqa: E402

GOLDEN_PADRAO = [c.id for c in casos.todos()]


def relatorio(versao: str, caso_id: str) -> dict:
    v = resolver(versao)
    a = atender(v, caso_id)
    c = casos.caso(caso_id)
    return {
        "versao": versao,
        "caso": caso_id,
        "status": a.status,
        "erro": a.erro,
        "decisao": a.decisao.model_dump(mode="json") if a.decisao else None,
        "resposta": a.resposta,
        "trajetoria": [
            {"agente": x.agente, "ferramenta": x.ferramenta, "args": x.args, "efetiva": x.efetiva}
            for x in a.trajetoria
        ],
        "fontes": a.fonte,
        "reprovados": reprovados(a, c),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--versao", default="v3")
    p.add_argument("--casos", nargs="*", default=GOLDEN_PADRAO)
    args = p.parse_args()
    saida = config.RAIZ / "rangoja" / "gravacoes" / args.versao
    saida.mkdir(parents=True, exist_ok=True)
    for caso_id in args.casos:
        r = relatorio(args.versao, caso_id)
        (saida / f"{caso_id}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        marca = "OK " if not r["reprovados"] and r["status"] != "erro" else "!! "
        print(f"{marca}{args.versao} {caso_id:<12} status={r['status']:<22} reprovados={list(r['reprovados'])}")


if __name__ == "__main__":
    main()
