"""Roteiros dos testes: o modelo simulado tenta o comportamento certo ou errado, e o sistema
precisa barrar o que não deve. Os passos dependem da forma da versão (com ou sem sequência)."""
from __future__ import annotations

import pytest

from rangoja.versoes import Versao


def requer(versao: Versao, *componentes: str) -> None:
    faltam = [c for c in componentes if c not in versao]
    if faltam:
        pytest.skip(f"não se aplica a {versao.nome}: falta {', '.join(faltam)}")


from rangoja.roteiros import atendimento, decisao, montar_roteiro, triagem  # noqa: E402,F401
