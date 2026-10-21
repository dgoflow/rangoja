"""Relógio controlável. Prazos e recorrência usam sempre agora(), nunca datetime.now()."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

INICIO_PADRAO = datetime(2026, 11, 10, 12, 0, tzinfo=timezone(timedelta(hours=-3)))

_estado = {"agora": INICIO_PADRAO}


def agora() -> datetime:
    return _estado["agora"]


def avancar(**kwargs: float) -> datetime:
    _estado["agora"] = _estado["agora"] + timedelta(**kwargs)
    return _estado["agora"]


def dormir(segundos: float) -> None:
    """Em replay o tempo é virtual: avança o relógio em vez de esperar."""
    avancar(seconds=segundos)


def reset(inicio: datetime | None = None) -> None:
    _estado["agora"] = inicio or INICIO_PADRAO
