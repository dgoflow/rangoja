"""Fixtures e opções comuns. Cada teste roda com armazém, relógio e falhas isolados."""
from __future__ import annotations

import os

import pytest

from rangoja import falhas, relogio, versoes
from rangoja.armazem import Armazem


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: exige modelo real (RANGOJA_MODO=live ou record e chave de API)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    from rangoja import config
    if config.modo() in ("live", "record") and config.chave_disponivel():
        return
    marcador = pytest.mark.skip(reason="teste live: requer RANGOJA_MODO=live ou record e chave de API (.env)")
    for item in items:
        # o marcador, não a palavra-chave: um parâmetro chamado "live" (ex.: test_modos[live]) também vira palavra-chave
        if item.get_closest_marker("live"):
            item.add_marker(marcador)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--versao", action="store", default=os.getenv("RANGOJA_VERSAO", "v3"),
                     help="versão a testar: v0..v3 ou variação (ex.: v2-contrato, v1+aprovacao)")


@pytest.fixture
def versao(request: pytest.FixtureRequest) -> versoes.Versao:
    return versoes.resolver(request.config.getoption("--versao"))


@pytest.fixture(autouse=True)
def _isolamento():
    Armazem.reset()
    relogio.reset()
    falhas.limpar()
    yield
    falhas.limpar()
