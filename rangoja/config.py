"""Configuração lida do ambiente (RANGOJA_*). Padrões seguros: modo replay, sem rede."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
DADOS = Path(__file__).resolve().parent / "dados"
CACHE = RAIZ / ".cache" / "modelo"
GRAVACOES = Path(__file__).resolve().parent / "gravacoes"
ROTEIROS = Path(__file__).resolve().parent / "roteiros"

MODOS = ("replay", "live", "record")

# .env na raiz do projeto (fora do git). Variáveis já definidas no ambiente têm prioridade.
load_dotenv(RAIZ / ".env", override=False)


def modo() -> str:
    valor = os.getenv("RANGOJA_MODO", "replay").strip().lower()
    if valor not in MODOS:
        raise ValueError(f"RANGOJA_MODO inválido: {valor!r}; use {MODOS}")
    return valor


def chave_disponivel() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def modelo_primario() -> str:
    return os.getenv("RANGOJA_MODELO", "gpt-4o-mini")


def modelo_fallback() -> str:
    return os.getenv("RANGOJA_MODELO_FALLBACK", "gpt-4.1-mini")


def modelo_juiz() -> str:
    return os.getenv("RANGOJA_MODELO_JUIZ", "gpt-4o")


def repeticoes() -> int:
    return int(os.getenv("RANGOJA_REPETICOES", "5"))


def limiar_estabilidade() -> float:
    return float(os.getenv("RANGOJA_LIMIAR_ESTABILIDADE", "0.8"))
