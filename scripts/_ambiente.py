"""Garante o modo e a chave antes de rodar scripts que chamam o modelo real."""
from __future__ import annotations

import os
import sys


def exigir_modo_ao_vivo(modo: str) -> None:
    os.environ["RANGOJA_MODO"] = modo
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rangoja import config
    if not config.chave_disponivel():
        sys.exit("Falta a chave de API. Coloque OPENAI_API_KEY no .env da raiz do projeto "
                 "(ver .env.example) e rode de novo.")
