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


def provedor() -> str:
    """openai ou gemini. Padrão: openai se houver OPENAI_API_KEY, senão gemini."""
    escolhido = os.getenv("RANGOJA_PROVEDOR", "").strip().lower()
    if escolhido:
        return escolhido
    return "openai" if os.getenv("OPENAI_API_KEY") else "gemini"


def chave_disponivel() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") if provedor() == "openai" else os.getenv("GOOGLE_API_KEY"))


_MODELOS_PADRAO = {
    "openai": {"primario": "gpt-4o-mini", "fallback": "gpt-4.1-mini", "juiz": "gpt-4o"},
    "gemini": {"primario": "gemini-2.5-flash", "fallback": "gemini-2.5-flash-lite", "juiz": "gemini-2.5-pro"},
}


def modelo_primario() -> str:
    return os.getenv("RANGOJA_MODELO", _MODELOS_PADRAO[provedor()]["primario"])


def modelo_fallback() -> str:
    return os.getenv("RANGOJA_MODELO_FALLBACK", _MODELOS_PADRAO[provedor()]["fallback"])


def modelo_juiz() -> str:
    return os.getenv("RANGOJA_MODELO_JUIZ", _MODELOS_PADRAO[provedor()]["juiz"])


def repeticoes() -> int:
    return int(os.getenv("RANGOJA_REPETICOES", "5"))


def limiar_estabilidade() -> float:
    return float(os.getenv("RANGOJA_LIMIAR_ESTABILIDADE", "0.8"))
