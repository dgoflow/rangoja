"""Gravações nomeadas: uma execução real (cadeia de respostas do modelo) guardada em JSON.

O arquivo é lido por `Roteiro.de_arquivo` e servido em ordem, por agente, em `replay`. Só a
cadeia de respostas do modelo é gravada; callbacks, ferramentas e orquestração rodam de verdade.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from . import contexto


def salvar(nome: str, ctx: contexto.Contexto, **metadados) -> Path | None:
    """Grava `gravacoes/<nome>.json` a partir das respostas da execução. None se não for gravável."""
    corpo = contexto.para_gravacao(
        ctx, nome=nome, modelo=config.modelo_primario(), provedor="openai",
        gravada_em=datetime.now(timezone.utc).isoformat(timespec="seconds"), **metadados,
    )
    if corpo is None:
        return None
    caminho = config.GRAVACOES / f"{nome}.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(corpo, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho
