"""Prova de que a bateria pega regressões: remove um componente e exige que o teste certo falhe.

Roda `test_orquestracao.py` em subprocesso contra `v2-contrato` (v2 sem o contrato de fronteira).
O único teste que deve quebrar é o de C06 (mensagem sem pedido): sem o contrato, o agente de
resolução decide mesmo sem `pedido_id`. Se nada falhar, a bateria deixou de proteger o contrato.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_remover_contrato_quebra_o_teste_de_c06():
    ambiente = {**os.environ, "RANGOJA_MODO": "replay"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_orquestracao.py", "--versao", "v2-contrato",
         "-q", "-rf", "-p", "no:cacheprovider"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True, timeout=300,
    )
    falhas = [linha for linha in proc.stdout.splitlines() if linha.startswith("FAILED")]
    assert proc.returncode != 0, f"nenhum teste falhou sem o contrato:\n{proc.stdout[-1500:]}"
    assert len(falhas) == 1 and "test_sem_pedido_nao_ha_decisao" in falhas[0], (
        f"esperava só test_sem_pedido_nao_ha_decisao falhando, veio:\n{proc.stdout[-1500:]}")
