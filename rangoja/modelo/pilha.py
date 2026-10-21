"""ModeloRangoja: a pilha do modelo, abaixo de todos os callbacks do ADK.

    fallback → retry → injeção de falhas → fonte (roteiro | gravação | cache | modelo ao vivo)

Como fica abaixo dos callbacks, guardrails, categorias e limites rodam em qualquer modo.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import ConfigDict

from .. import config, falhas, relogio
from . import contexto
from .roteiro import para_resposta


class RespostaAusente(Exception):
    """Nenhuma fonte tem resposta para esta requisição (modo replay)."""


MAX_TENTATIVAS = 3


def _chave(requisicao: Any) -> str:
    """Hash estável da requisição. `response_schema` pode conter classes (Pydantic): viram texto."""
    corpo = requisicao.model_dump(mode="python", exclude_none=True)
    return hashlib.sha256(json.dumps(corpo, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class ModeloRangoja(BaseLlm):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str = "rangoja-roteirizado"
    agente: str = "unico"
    papel: str = "primario"          # primario | secundario | juiz
    retry: bool = False
    fallback: Any = None             # ModeloRangoja | None

    async def generate_content_async(  # type: ignore[override]
        self, llm_request: Any, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        try:
            resposta = await self._chamar(llm_request)
        except (falhas.ErroTransitorio, falhas.ErroPermanente):
            if self.fallback is None:
                raise
            resposta = await self.fallback._chamar(llm_request)
        yield resposta

    async def _chamar(self, requisicao: Any) -> LlmResponse:
        ctx = contexto.atual()
        tentativa = 0
        while True:
            tentativa += 1
            try:
                erro = falhas.no_modelo(self.papel)
                if erro is not None:
                    raise erro
                resposta = await _fonte(self, requisicao)
                ctx.tentativas.append(tentativa)
                ctx.modelos.append(self.papel)
                return resposta
            except falhas.ErroTransitorio:
                if not self.retry or tentativa >= MAX_TENTATIVAS:
                    raise
                relogio.dormir(0.5 * 2 ** (tentativa - 1))


async def _fonte(modelo: ModeloRangoja, requisicao: Any) -> LlmResponse:
    resposta = await _fonte_interna(modelo, requisicao)
    contexto.atual().respostas.append((modelo.agente, resposta))
    return resposta


async def _fonte_interna(modelo: ModeloRangoja, requisicao: Any) -> LlmResponse:
    ctx = contexto.atual()
    for nome, origem in (("roteiro", ctx.roteiro), ("gravacao", ctx.gravacao)):
        if origem is None:
            continue
        passo = origem.proximo(modelo.agente, requisicao)
        if passo is not None:
            ctx.fontes.append(nome)
            return para_resposta(passo, requisicao)

    caminho = config.CACHE / f"{_chave(requisicao)}.json"
    # `record` sempre amostra o modelo de novo (senão repetições só reaproveitariam a 1ª resposta)
    if ctx.modo != "record" and caminho.exists():
        ctx.fontes.append("cache")
        return LlmResponse.model_validate_json(caminho.read_text(encoding="utf-8"))

    if ctx.modo == "replay":
        raise RespostaAusente(
            f"sem roteiro, gravação ou cache para o agente '{modelo.agente}' (modo replay). "
            "Rode em modo record para gerar o cache."
        )

    resposta = await _ao_vivo(modelo, requisicao)
    ctx.fontes.append("live")
    if ctx.modo == "record":
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(resposta.model_dump_json(exclude_none=True), encoding="utf-8")
    return resposta


async def _ao_vivo(modelo: ModeloRangoja, requisicao: Any) -> LlmResponse:
    """Caminho ao vivo: OpenAI via LiteLlm do ADK. Não exercitado nos testes replay; ver IMPLEMENTACAO.md."""
    nome = {"primario": config.modelo_primario(), "secundario": config.modelo_fallback()}.get(
        modelo.papel, config.modelo_juiz()
    )
    from google.adk.models.lite_llm import LiteLlm
    ia = LiteLlm(model=f"openai/{nome}")
    requisicao.model = f"openai/{nome}"  # o LiteLlm usa o modelo da requisição, não o seu
    final = await _uma_chamada(ia, requisicao)
    # O ADK entrega a saída estruturada por uma ferramenta (`set_model_response`). Se o modelo
    # responde em prosa em vez de chamá-la, pede de novo (até 2 vezes) em vez de quebrar o fluxo.
    for _ in range(2):
        if "set_model_response" not in getattr(requisicao, "tools_dict", {}) or _tem_chamada(final):
            break
        requisicao.contents.append(types.Content(role="user", parts=[types.Part(text=(
            "Sua resposta anterior não usou set_model_response. Responda chamando set_model_response "
            "com a decisão estruturada (use categoria 'indefinida' e solucao 'pedir_informacao' se "
            "faltar informação) e escreva o texto ao cliente em mensagem_ao_cliente."))]))
        final = await _uma_chamada(ia, requisicao)
    return final


def _tem_chamada(resposta: LlmResponse) -> bool:
    partes = resposta.content.parts if resposta.content and resposta.content.parts else []
    return any(p.function_call for p in partes)


async def _uma_chamada(ia: Any, requisicao: Any) -> LlmResponse:
    final: LlmResponse | None = None
    async for parcial in ia.generate_content_async(requisicao, stream=False):
        final = parcial
    assert final is not None
    return final
