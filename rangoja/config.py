"""Configuração lida do ambiente (RANGOJA_*). Padrões seguros: modo replay, sem rede."""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
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


@contextmanager
def em_modo(novo: str):
    """Troca o modo só dentro do bloco. A N0.2 confere o replay mesmo com `live` no .env."""
    if novo not in MODOS:
        raise ValueError(f"modo inválido: {novo!r}; use {MODOS}")
    anterior = os.environ.get("RANGOJA_MODO")
    os.environ["RANGOJA_MODO"] = novo
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("RANGOJA_MODO", None)
        else:
            os.environ["RANGOJA_MODO"] = anterior


def chave_disponivel() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def diagnostico_chave() -> str:
    """Diz em uma frase o estado da chave e o que fazer, sem nunca mostrar o valor."""
    if chave_disponivel():
        return f"chave presente ({len(os.environ['OPENAI_API_KEY'])} caracteres); modo {modo()}"
    env = RAIZ / ".env"
    if not env.exists():
        # caminho relativo: a mensagem fica salva nas saídas dos notebooks e não deve trazer a pasta de quem os executou
        return "sem chave e sem arquivo .env na raiz do projeto; rode config.configurar_chave() ou crie o .env"
    linhas = env.read_text(encoding="utf-8").splitlines()
    if any(ln.strip().startswith("OPENAI_API_KEY=") and ln.split("=", 1)[1].strip() for ln in linhas):
        return "o .env tem a chave, mas este kernel não a leu: reinicie o kernel e rode a primeira célula"
    return "o .env existe, mas a linha OPENAI_API_KEY está vazia ou comentada; preencha, ou rode config.configurar_chave()"


_validadas: dict[str, bool | None] = {}


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


def estado_chave() -> str:
    """Estado da chave em uma frase curta para a tabela do NB00 (valida uma vez por chave, sem gastar tokens)."""
    if not chave_disponivel():
        return "não (use replay)"
    chave = os.environ["OPENAI_API_KEY"]
    if chave not in _validadas:
        _validadas[chave] = validar_chave(chave, timeout=3.0)
    return {True: "sim, validada", False: "sim, mas a OpenAI a recusou (confira o valor)",
            None: "sim, não validada (sem rede?)"}[_validadas[chave]]


def usar_live() -> str:
    """Liga o modo live neste kernel, se houver chave que a OpenAI não recuse."""
    if not chave_disponivel():
        return "sem chave: continua em replay"
    if estado_chave().startswith("sim, mas"):
        return "a OpenAI recusou a chave: continua em replay"
    os.environ["RANGOJA_MODO"] = "live"
    return "modo live ligado neste kernel"


def gravar_env(valores: dict[str, str], arquivo: Path | None = None) -> Path:
    """Grava as variáveis no .env da raiz, preservando o resto do arquivo. Cria com permissão 600."""
    arquivo = arquivo or RAIZ / ".env"
    linhas = arquivo.read_text(encoding="utf-8").splitlines() if arquivo.exists() else []
    for nome, valor in valores.items():
        nova = f"{nome}={valor}"
        for padrao in (rf"^\s*{nome}\s*=", rf"^\s*#\s*{nome}\s*="):  # linha ativa; senão o modelo comentado
            achou = next((i for i, ln in enumerate(linhas) if re.match(padrao, ln)), None)
            if achou is not None:
                linhas[achou] = nova
                break
        else:
            linhas.append(nova)
    arquivo.touch(mode=0o600, exist_ok=True)
    arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    arquivo.chmod(0o600)
    return arquivo


def configurar_chave(chave: str | None = None, salvar: bool | None = None, arquivo: Path | None = None) -> str:
    """Pede a chave com entrada oculta e liga o modo live neste kernel.

    Cada notebook tem seu kernel, então a chave só passa para os outros se for salva no .env.
    `salvar=None` pergunta (só quando a chave é digitada aqui); a resposta padrão é não.
    """
    perguntar = chave is None
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
    _validadas[chave] = resultado
    msg = ("chave válida" if resultado else "chave guardada, mas não consegui validá-la (sem rede?)") + "; modo live ligado neste kernel"
    if salvar is None and perguntar:
        try:
            salvar = input("Salvar no .env para os outros notebooks usarem? A chave fica em texto no disco. [s/N] ").strip().lower() in ("s", "sim", "y")
        except Exception:
            salvar = False
    if salvar:
        destino = gravar_env({"OPENAI_API_KEY": chave, "RANGOJA_MODO": "live"}, arquivo)
        onde = destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino  # sem a pasta de quem roda
        msg += f"; salva em {onde} (permissão 600)"
    else:
        msg += "; vale só para este notebook (os outros vão pedir de novo)"
    return msg


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
