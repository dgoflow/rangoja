"""Confere se as gravações nomeadas ainda servem ao código atual (roda em replay, sem rede).

Para cada gravação usada por uma seção, atende o caso com a versão certa e verifica que:
  - o atendimento não terminou em erro de gravação/roteiro (esgotada ou ausente);
  - todas as respostas gravadas foram consumidas (sobra = a versão passou a chamar menos o modelo).
Também confere que as gravações dos relatórios de golden (`gravacoes/v3/*.json`) são JSON válido.

    .venv/bin/python scripts/verificar_gravacoes.py          # sai com 1 se alguma estiver desatualizada
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

os.environ["RANGOJA_MODO"] = "replay"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rangoja import config  # noqa: E402
from rangoja.execucao import atender  # noqa: E402
from rangoja.modelo.roteiro import Roteiro  # noqa: E402
from rangoja.notebook import preparar_secao  # noqa: E402
from rangoja.secoes import SECOES  # noqa: E402
from rangoja.versoes import v1  # noqa: E402


def _alvo(spec, rotulo: str):
    """(versão, caso) em que a gravação `rotulo` da seção foi feita."""
    if rotulo == "v1_gravada":
        return v1, spec.caso
    base, _, sufixo = rotulo.partition("_")
    caso = spec.casos_extra.get(sufixo or rotulo, spec.caso)
    if rotulo in spec.casos_extra:      # ex.: "c10" = correção aplicada a outro caso
        return spec.correcao, caso
    versao = spec.falha if base == "falha" else spec.correcao
    return versao, caso


def verificar() -> list[str]:
    problemas: list[str] = []
    vistas: set[str] = set()
    for spec in SECOES.values():
        for rotulo, nome in spec.gravacoes.items():
            if nome in vistas:
                continue
            vistas.add(nome)
            caminho = config.GRAVACOES / f"{nome}.json"
            if not caminho.exists():
                problemas.append(f"{nome}: arquivo ausente ({spec.id}/{rotulo})")
                continue
            versao, caso = _alvo(spec, rotulo)
            with contextlib.redirect_stdout(io.StringIO()):
                preparar_secao(spec.id)
            roteiro = Roteiro.de_arquivo(caminho)
            a = atender(versao, caso, gravacao=roteiro)
            erro = (a.erro or "")
            if a.status == "erro" and ("esgotad" in erro or "ausente" in erro.lower()):
                problemas.append(f"{nome}: desatualizada ({erro[:120]})")
                continue
            sobras = {ag: len(p) - roteiro._cursor.get(ag, 0) for ag, p in roteiro.passos.items()
                      if len(p) > roteiro._cursor.get(ag, 0)}
            if sobras:
                problemas.append(f"{nome}: respostas não consumidas {sobras} (versão {versao.nome}, caso {caso})")
    for arquivo in sorted((config.GRAVACOES / "v3").glob("*.json")):
        try:
            json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError as exc:
            problemas.append(f"v3/{arquivo.name}: JSON inválido ({exc})")
    return problemas


if __name__ == "__main__":
    ruins = verificar()
    for p in ruins:
        print("✗", p)
    print(f"{'FALHOU' if ruins else 'OK'}: {len(ruins)} problema(s)")
    sys.exit(1 if ruins else 0)
