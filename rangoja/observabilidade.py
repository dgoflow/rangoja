"""Observabilidade: Phoenix local + instrumentação OpenInference do ADK. Nunca lança exceção."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any

PORTA = int(os.getenv("RANGOJA_PHOENIX_PORTA", "6006"))
_estado: dict[str, Any] = {"ligado": False, "motivo": "não ligado"}


def _porta_aberta(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def ligar() -> str:
    """Sobe o Phoenix local (se preciso), registra o tracer e instrumenta o ADK. Devolve um resumo."""
    if _estado["ligado"]:
        return _estado["motivo"]
    if os.getenv("RANGOJA_PHOENIX", "on").lower() == "off":
        _estado["motivo"] = "desligado (RANGOJA_PHOENIX=off)"
        return _estado["motivo"]
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        import phoenix  # noqa: F401  (o servidor local)
    except Exception as exc:  # pacotes opcionais ausentes
        _estado["motivo"] = f"indisponível ({type(exc).__name__}); usando anatomia em texto"
        return _estado["motivo"]
    try:
        if not _porta_aberta(PORTA):
            env = {**os.environ, "PHOENIX_PORT": str(PORTA),
                   "PHOENIX_WORKING_DIR": tempfile.mkdtemp(prefix="rangoja-phoenix-")}
            subprocess.Popen([sys.executable, "-m", "phoenix.server.main", "serve"], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(60):
                if _porta_aberta(PORTA):
                    break
                time.sleep(0.5)
        if not _porta_aberta(PORTA):
            raise RuntimeError("servidor do Phoenix não subiu")
        # exportador OTLP/HTTP direto, sem phoenix.otel (que exige uma versão do SDK de OpenTelemetry
        # diferente da que o ADK fixa); o projeto no Phoenix vem do atributo de recurso abaixo
        provedor = TracerProvider(resource=Resource.create({"openinference.project.name": "rangoja"}))
        provedor.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=f"http://127.0.0.1:{PORTA}/v1/traces")))
        GoogleADKInstrumentor().instrument(tracer_provider=provedor)
        _estado.update(ligado=True, motivo=f"ligado em http://127.0.0.1:{PORTA}")
    except Exception as exc:
        _estado["motivo"] = f"falhou ({type(exc).__name__}: {exc}); usando anatomia em texto"
    return _estado["motivo"]


def ligado() -> bool:
    return bool(_estado["ligado"])


def url() -> str | None:
    return f"http://127.0.0.1:{PORTA}/projects" if ligado() else None


def _titulo_versao(atendimento) -> str:
    versao = getattr(atendimento, "_versao", None)
    return versao.titulo if versao is not None else atendimento.versao


def anatomia(atendimento) -> str:
    """Árvore textual do atendimento: agente → modelo → ferramenta. Serve com ou sem Phoenix."""
    linhas = [f"atendimento {atendimento.caso_id} ({_titulo_versao(atendimento)}) — status: {atendimento.status}"]
    ultimo = None
    for ev in atendimento.eventos:
        if not ev.content or not ev.content.parts:
            continue
        if ev.author != ultimo:
            linhas.append(f"├─ agente {ev.author}")
            ultimo = ev.author
        for p in ev.content.parts:
            if p.function_call:
                linhas.append(f"│   ├─ pede ferramenta {p.function_call.name}({dict(p.function_call.args or {})})")
            elif p.function_response:
                resumo = str(p.function_response.response)[:90]
                linhas.append(f"│   ├─ resultado de {p.function_response.name}: {resumo}")
            elif p.text:
                linhas.append(f"│   └─ texto: {p.text[:90]!r}")
    fontes = ", ".join(sorted(set(atendimento.fonte))) or "—"
    linhas.append(f"└─ fonte das respostas do modelo: {fontes}")
    return "\n".join(linhas)
