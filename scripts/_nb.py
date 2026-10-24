"""Utilidades para gerar e executar notebooks."""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "notebooks"

SETUP = '''from rangoja import config, dados, falhas, ferramentas, controle, observabilidade, relogio
from rangoja.armazem import Armazem
from rangoja.casos import caso
from rangoja.execucao import atender, atender_caso, continuar, aprovar, recusar, expirar_pendencias, reiniciar_runner, estado_persistido
from rangoja.notebook import (preparar_ambiente, preparar_secao, mostrar, comparar, afirmar, esperar, verificar, verificar_falha,
                              resumo, amostra, matriz)
from rangoja.trajetoria import chamou, ferramenta_antes, contar_chamadas
from rangoja.versoes import v0, v1, v2, v3, v0_so_prompt, v1_agente, v2_controlado, v3_robusto, montar
preparar_ambiente()'''

AVISO = ("> ▶ **Comece por aqui:** execute a célula de código abaixo **uma vez**, antes de qualquer seção. "
         "Ela importa tudo que os exemplos usam (`atender_caso`, `afirmar`, …). Depois disso, cada seção roda sozinha, na ordem que você quiser.")
COMENTARIO = "# Execute esta célula primeiro: ela importa o que todas as seções usam.\n"


def md(texto: str):
    return nbf.v4.new_markdown_cell(texto.strip())


def code(texto: str):
    return nbf.v4.new_code_cell(texto.strip())


def setup():
    return code(COMENTARIO + SETUP)


def com_aviso(celulas: list) -> list:
    """Põe o aviso de 'execute primeiro' antes da célula de preparação."""
    saida = []
    for c in celulas:
        if c.cell_type == "code" and c.source.startswith(COMENTARIO):
            saida.append(md(AVISO))
        saida.append(c)
    return saida


def salvar(nome: str, celulas: list) -> Path:
    nb = nbf.v4.new_notebook()
    nb.cells = com_aviso(celulas)
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    caminho = PASTA / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, caminho)
    return caminho
