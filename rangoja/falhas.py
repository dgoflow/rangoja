"""Injeção de falhas para demonstração e testes. Sempre usada como `with falhas.injetar(...)`.

Os tipos e efeitos estão em notebooks/specs/03_falhas_e_observabilidade.md.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Optional


class ErroTransitorio(Exception):
    """Falha que vale a pena repetir (429, timeout)."""


class ErroPermanente(Exception):
    """Falha que não se resolve repetindo (modelo fora do ar)."""


TIPOS_MODELO = {"modelo_429", "modelo_timeout", "modelo_fora"}
TIPOS_FERRAMENTA = {"ferramenta_fora", "resultado_ambiguo", "timeout_apos_efeito"}


@dataclass
class _Injecao:
    tipo: str
    alvo: Optional[str]
    vezes: Optional[int]  # None = sempre
    usos: int = 0

    def disponivel(self) -> bool:
        return self.vezes is None or self.usos < self.vezes


_ativas: ContextVar[list[_Injecao]] = ContextVar("falhas_ativas")


def _lista() -> list[_Injecao]:
    try:
        return _ativas.get()
    except LookupError:
        nova: list[_Injecao] = []
        _ativas.set(nova)
        return nova


@contextmanager
def injetar(tipo: str, *, alvo: Optional[str] = None, vezes: Optional[int] = None) -> Iterator[None]:
    if tipo not in TIPOS_MODELO | TIPOS_FERRAMENTA:
        raise ValueError(f"tipo de falha desconhecido: {tipo}")
    lista = _lista()
    injecao = _Injecao(tipo=tipo, alvo=alvo, vezes=vezes if vezes is not None else (1 if tipo in {"modelo_429", "modelo_timeout", "timeout_apos_efeito"} else None))
    lista.append(injecao)
    try:
        yield
    finally:
        lista.remove(injecao)


def no_modelo(papel: str) -> Optional[Exception]:
    """Exceção a lançar na chamada ao modelo `papel`, se houver falha injetada."""
    for inj in _lista():
        if inj.tipo not in TIPOS_MODELO or not inj.disponivel():
            continue
        alvo = inj.alvo or "primario"
        if alvo != papel:
            continue
        inj.usos += 1
        if inj.tipo == "modelo_429":
            return ErroTransitorio("429 Too Many Requests (injetado)")
        if inj.tipo == "modelo_timeout":
            return ErroTransitorio("timeout (injetado)")
        return ErroPermanente("503 modelo indisponível (injetado)")
    return None


def na_ferramenta(nome: str) -> None:
    """Chamada no início de cada ferramenta: pode lançar a falha injetada."""
    for inj in _lista():
        if inj.tipo == "ferramenta_fora" and inj.alvo == nome and inj.disponivel():
            inj.usos += 1
            raise ConnectionError(f"{nome}: serviço indisponível (injetado)")


def ferramenta_ambigua(nome: str) -> bool:
    for inj in _lista():
        if inj.tipo == "resultado_ambiguo" and inj.alvo == nome and inj.disponivel():
            inj.usos += 1
            return True
    return False


def apos_efeito(nome: str) -> None:
    """Chamada depois do efeito de uma ferramenta: simula confirmação perdida."""
    for inj in _lista():
        if inj.tipo == "timeout_apos_efeito" and inj.alvo == nome and inj.disponivel():
            inj.usos += 1
            raise TimeoutError(f"{nome}: confirmação perdida após o efeito (injetado)")


def limpar() -> None:
    _lista().clear()
