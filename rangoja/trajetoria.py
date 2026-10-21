"""Trajetória de um atendimento: chamadas de ferramenta, em ordem, com efeito real ou não."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

INTERNAS = {"set_model_response", "transfer_to_agent", "adk_request_confirmation"}


@dataclass(frozen=True)
class Chamada:
    agente: str
    ferramenta: str
    args: dict[str, Any] = field(hash=False, compare=False)
    resultado: Any = field(hash=False, compare=False)
    erro: str | None = None
    efetiva: bool = True


def extrair(eventos: Iterable[Any]) -> list[Chamada]:
    pendentes: dict[str, tuple[str, str, dict]] = {}
    saida: list[Chamada] = []
    for ev in eventos:
        if not ev.content or not ev.content.parts:
            continue
        for parte in ev.content.parts:
            if parte.function_call and parte.function_call.name not in INTERNAS:
                fc = parte.function_call
                pendentes[fc.id or fc.name] = (ev.author, fc.name, dict(fc.args or {}))
            if parte.function_response and parte.function_response.name not in INTERNAS:
                fr = parte.function_response
                agente, nome, args = pendentes.pop(fr.id or fr.name, (ev.author, fr.name, {}))
                resposta = fr.response or {}
                bloqueado = isinstance(resposta, dict) and (
                    "bloqueado" in resposta or "erro" in resposta
                    or resposta.get("status") == "aguardando_aprovacao"
                )
                saida.append(Chamada(
                    agente=agente, ferramenta=nome, args=args, resultado=resposta,
                    erro=(resposta.get("erro") if isinstance(resposta, dict) else None),
                    efetiva=not bloqueado,
                ))
    return saida


def chamou(trajetoria: Iterable[Chamada], ferramenta: str, *, efetiva: bool = True) -> bool:
    return any(c.ferramenta == ferramenta and (c.efetiva or not efetiva) for c in trajetoria)


def contar_chamadas(trajetoria: Iterable[Chamada], ferramenta: str, *, efetivas: bool = True) -> int:
    return sum(1 for c in trajetoria if c.ferramenta == ferramenta and (c.efetiva or not efetivas))


def ferramenta_antes(trajetoria: Iterable[Chamada], anterior: str, posterior: str) -> bool:
    """Toda chamada efetiva de `posterior` tem uma chamada efetiva de `anterior` antes dela."""
    visto_anterior = False
    for c in trajetoria:
        if c.ferramenta == anterior and c.efetiva:
            visto_anterior = True
        if c.ferramenta == posterior and c.efetiva and not visto_anterior:
            return False
    return True
