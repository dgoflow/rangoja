"""Utilidades para gerar e executar notebooks."""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "notebooks"

SETUP = '''from rangoja import config, dados, falhas, ferramentas, controle, observabilidade, relogio
from rangoja.armazem import Armazem
from rangoja.casos import caso
from rangoja.execucao import atender, continuar, aprovar, recusar, expirar_pendencias, reiniciar_runner, estado_persistido
from rangoja.notebook import (preparar_ambiente, preparar_secao, mostrar, verificar, verificar_falha,
                              resumo, amostra, matriz)
from rangoja.trajetoria import chamou, ferramenta_antes, contar_chamadas
from rangoja.versoes import v0, v1, v2, v3, montar
preparar_ambiente()'''


def md(texto: str):
    return nbf.v4.new_markdown_cell(texto.strip())


def code(texto: str):
    return nbf.v4.new_code_cell(texto.strip())


def setup():
    return code(SETUP)


def salvar(nome: str, celulas: list) -> Path:
    nb = nbf.v4.new_notebook()
    nb.cells = celulas
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    caminho = PASTA / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, caminho)
    return caminho
