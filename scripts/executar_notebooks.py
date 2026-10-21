"""Executa notebooks em modo replay e grava as saídas no próprio arquivo.

    .venv/bin/python scripts/executar_notebooks.py 00_ambiente.ipynb 01_do_prompt_ao_agente.ipynb
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "notebooks"


def executar(nome: str) -> bool:
    caminho = PASTA / nome
    pasta = caminho.parent
    nb = nbformat.read(caminho, as_version=4)
    os.environ["RANGOJA_MODO"] = "replay"
    cliente = NotebookClient(nb, timeout=900, kernel_name="rangoja", resources={"metadata": {"path": str(pasta)}})
    try:
        cliente.execute()
        ok = True
    except CellExecutionError as exc:
        print(f"ERRO em {nome}:\n{str(exc)[-1500:]}")
        ok = False
    nbformat.write(nb, caminho)
    print(("OK   " if ok else "FALHA"), nome)
    return ok


if __name__ == "__main__":
    nomes = sys.argv[1:] or sorted(p.name for p in PASTA.glob("0*.ipynb"))  # extras: extras/x1_....ipynb
    sys.exit(0 if all([executar(n) for n in nomes]) else 1)
