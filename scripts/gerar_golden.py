"""Gera evals/golden.yaml a partir de dados/casos.yaml (a fonte de verdade)."""
from __future__ import annotations

from pathlib import Path

import yaml

from rangoja import casos

SAIDA = Path(__file__).resolve().parent.parent / "evals" / "golden.yaml"


def main() -> None:
    itens = []
    for c in casos.todos():
        itens.append({
            "id": c.id,
            "cliente_id": c.cliente_id,
            "pedido_id": c.pedido_id,
            "atendimentos": c.atendimentos,
            "esperado": c.esperado,
            "usado_em": c.usado_em,
            "origem": c.origem,
            "relacao": c.relacao,
        })
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "# Gerado por scripts/gerar_golden.py a partir de rangoja/dados/casos.yaml. Não editar à mão.\n"
        + yaml.safe_dump(itens, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{len(itens)} casos em {SAIDA}")


if __name__ == "__main__":
    main()
