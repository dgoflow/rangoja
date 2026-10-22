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

# .env na raiz do projeto (fora do git). Variáveis já definidas no ambiente têm prioridade,
# exceto a chave vazia (um `export OPENAI_API_KEY=` esquecido não pode esconder a do .env).
if not os.environ.get("OPENAI_API_KEY"):
    os.environ.pop("OPENAI_API_KEY", None)
load_dotenv(RAIZ / ".env", override=False)


def modo() -> str:
    valor = os.getenv("RANGOJA_MODO", "replay").strip().lower()
    if valor not in MODOS:
        raise ValueError(f"RANGOJA_MODO inválido: {valor!r}; use {MODOS}")
    return valor


def chave_disponivel() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def diagnostico_chave() -> str:
    """Diz em uma frase o estado da chave e o que fazer, sem nunca mostrar o valor."""
    if chave_disponivel():
        return f"chave presente ({len(os.environ['OPENAI_API_KEY'])} caracteres); modo {modo()}"
    env = RAIZ / ".env"
    if not env.exists():
        return f"sem chave e sem arquivo {env}; rode config.configurar_chave() ou crie o .env"
    linhas = env.read_text(encoding="utf-8").splitlines()
    if any(ln.strip().startswith("OPENAI_API_KEY=") and ln.split("=", 1)[1].strip() for ln in linhas):
        return "o .env tem a chave, mas este kernel não a leu: reinicie o kernel e rode a primeira célula"
    return "o .env existe, mas a linha OPENAI_API_KEY está vazia ou comentada; preencha, ou rode config.configurar_chave()"


def validar_chave(chave: str, timeout: float = 8.0) -> bool | None:
    """Testa a chave contra a OpenAI sem gastar tokens. True/False; None se não deu para saber (sem rede)."""
    import urllib.error
    import urllib.request
    pedido = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {chave}"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout):
            return True
    except urllib.error.HTTPError as exc:
        return False if exc.code in (401, 403) else None
    except Exception:
        return None


def configurar_chave(chave: str | None = None) -> str:
    """Pede a chave com entrada oculta e liga o modo live neste kernel. Nada vai para disco nem para a saída.

    Serve para quem não quer editar o .env (nem reiniciar o kernel). Vale só até o kernel fechar.
    """
    if chave is None:
        from getpass import getpass
        try:
            chave = getpass("Cole sua OPENAI_API_KEY (a entrada fica oculta; Enter vazio mantém o replay): ")
        except Exception:  # execução sem teclado (CI, nbmake): segue em replay
            return "sem entrada interativa: continua em replay"
    chave = chave.strip()
    if not chave:
        return "nenhuma chave informada: continua em replay"
    resultado = validar_chave(chave)
    if resultado is False:
        return "a OpenAI recusou essa chave (confira se copiou inteira); continua como estava"
    os.environ["OPENAI_API_KEY"] = chave
    os.environ["RANGOJA_MODO"] = "live"
    if resultado is None:
        return "chave guardada, mas não consegui validá-la (sem rede?); modo live ligado neste kernel"
    return "chave válida; modo live ligado neste kernel"


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
