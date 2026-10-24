"""Execução de atendimentos. API síncrona para notebooks e testes.

O ADK é assíncrono. Cada chamada roda numa thread de trabalho com `asyncio.run`, num contexto
copiado do chamador, para que o contexto de execução (modo, roteiro, falhas injetadas) chegue
até a pilha do modelo mesmo dentro do Jupyter (que já tem um loop em execução).

Aprovação humana (acima do limite) não usa a confirmação de ferramenta do ADK: a pendência vai
para a fila do armazém (tabela `pendencias`) e aprovar/recusar/expirar agem sobre ela. Ver
notebooks/specs/02_controle.md e specs/pacote/03_componentes_versoes.md.
"""
from __future__ import annotations

import asyncio
import contextvars
import os
import tempfile
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import casos as casos_mod
from . import config, controle, ferramentas, relogio, versoes
from .armazem import Armazem
from .modelo import contexto
from .modelo.roteiro import Roteiro
from .tipos import Decisao
from .trajetoria import Chamada, extrair

APP = "rangoja"
PRAZO_APROVACAO = timedelta(hours=24)
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rangoja")


@dataclass
class Turno:
    mensagem: str
    resposta: str | None


@dataclass
class Atendimento:
    versao: str
    caso_id: str
    cliente_id: str
    sessao_id: str
    status: str
    decisao: Decisao | None
    resposta: str | None
    turnos: list[Turno]
    trajetoria: list[Chamada]
    estado: dict[str, Any]
    eventos: list[Any]
    fonte: list[str] = field(default_factory=list)
    modelos_usados: list[str] = field(default_factory=list)
    tentativas: list[int] = field(default_factory=list)
    erro: str | None = None
    pendencia: dict[str, Any] | None = None
    anteriores: list["Atendimento"] = field(default_factory=list)
    trace_url: str | None = None
    # interno: o necessário para continuar a conversa
    _servico: Any = field(default=None, repr=False)
    _runner: Any = field(default=None, repr=False)
    _run_config: Any = field(default=None, repr=False)
    _construida: Any = field(default=None, repr=False)
    _versao: Any = field(default=None, repr=False)
    _db: str | None = field(default=None, repr=False)


def _rodar(coro_factory):
    ctx = contextvars.copy_context()
    return _pool.submit(ctx.run, asyncio.run, coro_factory()).result()


def _mensagem(texto: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=texto)])


async def _enviar(runner: Runner, user_id: str, sessao_id: str, conteudo: types.Content, run_config: RunConfig):
    eventos = []
    try:
        async for ev in runner.run_async(user_id=user_id, session_id=sessao_id, new_message=conteudo, run_config=run_config):
            eventos.append(ev)
        return eventos, None
    except Exception as exc:  # erro vira status, nunca exceção para o notebook
        if os.getenv("RANGOJA_DEBUG"):
            traceback.print_exc()
        return eventos, f"{type(exc).__name__}: {exc}"


def _texto_final(eventos) -> str | None:
    """Última fala do cliente: texto final de um agente que não é a triagem nem a resolução."""
    texto = None
    for ev in eventos:
        if ev.content and ev.content.parts and not ev.partial and ev.author in ("resposta", "unico"):
            t = " ".join(p.text for p in ev.content.parts if p.text)
            if t and not (ev.author == "unico" and t.lstrip().startswith("{")):  # JSON da decisão não é fala
                texto = t
    return texto


def _pendencia_aberta(sessao_id: str) -> dict[str, Any] | None:
    for linha in Armazem.atual().linhas("pendencias", sessao_id=sessao_id):
        if linha["resolvida_em"] is None:
            return {**linha, "args": __import__("json").loads(linha["args_json"])}
    return None


def _status(state: dict[str, Any], pendencia: dict | None, erro: str | None) -> str:
    if erro:
        return "erro"
    if pendencia:
        return "aguardando_aprovacao"
    return state.get("status", "concluido")


def _resposta(decisao: Decisao | None, texto: str | None, state: dict[str, Any]) -> str | None:
    """Prefere a fala da etapa de resposta; a mensagem da decisão só vale no agente único.
    A proteção de dados do entregador é do componente guardrail_saida, não daqui."""
    if state.get("interrompido") and state.get("mensagem_pendente"):
        return state["mensagem_pendente"]
    if texto:
        return texto
    if decisao is not None and decisao.mensagem_ao_cliente:
        return decisao.mensagem_ao_cliente
    return None


def _ler_roteiro(roteiro, gravacao) -> tuple[Roteiro | None, Roteiro | None]:
    if isinstance(roteiro, dict):
        roteiro = Roteiro(roteiro)
    if isinstance(gravacao, str):
        gravacao = Roteiro.de_arquivo(config.GRAVACOES / f"{gravacao}.json")
    return roteiro, gravacao


def atender(versao, caso, *, roteiro=None, gravacao=None, cliente_id: str | None = None,
            temperatura: float | None = None) -> Atendimento:
    """Roda todos os atendimentos e turnos do caso. Nunca lança: erro vira status='erro'."""
    versao_obj = versao if isinstance(versao, versoes.Versao) else versoes.resolver(versao)
    caso_obj = casos_mod.caso(caso) if isinstance(caso, str) else caso
    cliente = cliente_id or caso_obj.cliente_id
    rot, grav = _ler_roteiro(roteiro, gravacao)
    ctx = contexto.Contexto(modo=config.modo(), roteiro=rot, gravacao=grav, temperatura=temperatura)
    contexto.definir(ctx)
    construida = versao_obj.construir()
    # um serviço de sessões por caso: o estado do usuário (user:) atravessa os atendimentos
    db = None
    if "persistencia" in versao_obj:
        _sessoes_dir().mkdir(parents=True, exist_ok=True)
        db = str(_sessoes_dir() / f"{uuid.uuid4().hex}.db")
    servico = _servico_sessoes(versao_obj, db)
    runner = Runner(app_name=APP, agent=construida.agente_raiz, session_service=servico)
    anteriores: list[Atendimento] = []
    for mensagens in caso_obj.atendimentos:
        anteriores.append(_rodar_atendimento(versao_obj, caso_obj.id, cliente, mensagens, construida, ctx,
                                             servico, runner, db))
    ultimo = anteriores[-1]
    ultimo.anteriores = anteriores[:-1]
    return ultimo


def atender_caso(caso, com, replay=None, *, roteiro=None, cliente_id: str | None = None,
                 temperatura: float | None = None) -> Atendimento:
    """Atende um caso do RangoJá com um agente: `atender_caso("C01", com=v0_so_prompt, replay="N1.1/falha")`.

    `caso` é o id (ou o objeto) do catálogo; `com` é a versão do agente; `replay` é a gravação usada em modo
    `replay`, sem rede e sem chave. Em `live` e `record` ela é ignorada: o modelo responde de verdade.
    É `atender` com nomes que se leem como frase."""
    return atender(com, caso, roteiro=roteiro, gravacao=replay, cliente_id=cliente_id, temperatura=temperatura)


def _nova_sessao(servico, cliente: str) -> str:
    sid = uuid.uuid4().hex
    _rodar(lambda: servico.create_session(
        app_name=APP, user_id=cliente, session_id=sid,
        state={"cliente_id": cliente, "sessao_id": sid},
    ))
    return sid


def _sessoes_dir() -> Path:
    return Path(tempfile.gettempdir()) / "rangoja-sessoes"


def _servico_sessoes(versao_obj, db: str | None):
    """Sem `persistencia`: sessões em memória. Com: SQLite, que sobrevive à queda do runner."""
    if "persistencia" in versao_obj and db is not None:
        from google.adk.sessions.sqlite_session_service import SqliteSessionService
        return SqliteSessionService(db_path=db)
    return InMemorySessionService()


def _rodar_atendimento(versao_obj, caso_id, cliente, mensagens, construida, ctx,
                       servico, runner, db) -> Atendimento:
    sessao_id = _nova_sessao(servico, cliente)
    turnos: list[Turno] = []
    eventos_totais: list[Any] = []
    erro = None
    for texto in mensagens:
        if "estado" not in versao_obj:
            sessao_id = _nova_sessao(servico, cliente)  # sem estado: cada mensagem abre sessão nova (N1.5)
        eventos, erro = _rodar(lambda: _enviar(runner, cliente, sessao_id, _mensagem(texto), construida.run_config))
        eventos_totais.extend(eventos)
        turnos.append(Turno(texto, _texto_final(eventos)))
        if erro or _pendencia_aberta(sessao_id):
            break
    at = _montar(versao_obj.nome, caso_id, cliente, sessao_id, turnos, eventos_totais, erro, ctx,
                 servico=servico, runner=runner, run_config=construida.run_config)
    at._construida = construida
    at._versao = versao_obj
    at._db = db
    return at


def _montar(versao: str, caso_id: str, cliente: str, sessao_id: str, turnos, eventos, erro, ctx,
            *, servico, runner, run_config, anteriores=None) -> Atendimento:
    sessao = _rodar(lambda: servico.get_session(app_name=APP, user_id=cliente, session_id=sessao_id))
    state = dict(sessao.state) if sessao else {}
    decisao = controle.decisao_do_estado(state)
    pendencia = _pendencia_aberta(sessao_id)
    return Atendimento(
        versao=versao, caso_id=caso_id, cliente_id=cliente, sessao_id=sessao_id,
        status=_status(state, pendencia, erro), decisao=decisao,
        resposta=_resposta(decisao, turnos[-1].resposta if turnos else None, state),
        turnos=list(turnos), trajetoria=extrair(eventos), estado=state, eventos=list(eventos),
        fonte=list(ctx.fontes), modelos_usados=list(ctx.modelos), tentativas=list(ctx.tentativas),
        erro=erro, pendencia=pendencia, anteriores=list(anteriores or []),
        _servico=servico, _runner=runner, _run_config=run_config,
    )


def continuar(atendimento: Atendimento, mensagem: str) -> Atendimento:
    """Mais um turno na mesma sessão (só com o componente `estado`)."""
    if atendimento._runner is None:
        if atendimento._db is None:
            raise RuntimeError("runner reiniciado e sem persistência: a conversa em memória foi perdida")
        atendimento._servico = _servico_sessoes(atendimento._versao, atendimento._db)
        atendimento._runner = Runner(app_name=APP, agent=atendimento._construida.agente_raiz,
                                     session_service=atendimento._servico)
    eventos, erro = _rodar(lambda: _enviar(
        atendimento._runner, atendimento.cliente_id, atendimento.sessao_id,
        _mensagem(mensagem), atendimento._run_config,
    ))
    turnos = list(atendimento.turnos) + [Turno(mensagem, _texto_final(eventos))]
    previos = [e for e in atendimento.eventos]
    novo = _montar(atendimento.versao, atendimento.caso_id, atendimento.cliente_id, atendimento.sessao_id,
                   turnos, previos + list(eventos), erro, contexto.atual(),
                   servico=atendimento._servico, runner=atendimento._runner,
                   run_config=atendimento._run_config, anteriores=atendimento.anteriores)
    novo._construida, novo._db, novo._versao = atendimento._construida, atendimento._db, atendimento._versao
    return novo


def _pendencia_ou_erro(at: Atendimento) -> dict[str, Any]:
    pend = _pendencia_aberta(at.sessao_id)
    if pend is None:
        raise ValueError("este atendimento não tem aprovação pendente")
    return pend


def _fechar(at: Atendimento, status: str, resposta: str, decisao_extra: str) -> Atendimento:
    novo = Atendimento(**{**at.__dict__, "status": status, "resposta": resposta, "pendencia": None,
                          "estado": {**at.estado, "status": status, "decisao_humana": decisao_extra}})
    return novo


def _reais(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def aprovar(atendimento: Atendimento) -> Atendimento:
    """Aprovação humana: efetiva o reembolso que estava na fila."""
    pend = _pendencia_ou_erro(atendimento)
    args = pend["args"]
    resultado = ferramentas.efetivar_reembolso(args["pedido_id"], args["valor"], args["motivo"], idempotente=True)
    Armazem.atual().con.execute(
        "UPDATE pendencias SET resolvida_em=?, resolucao=? WHERE id=?",
        (relogio.agora().isoformat(), "aprovada", pend["id"]),
    )
    Armazem.atual().con.commit()
    if resultado.get("status") not in ("registrado", "ja_registrado"):
        return _fechar(atendimento, "erro", f"Não foi possível registrar o reembolso: {resultado}", "aprovada")
    return _fechar(atendimento, "concluido",
                   f"Seu reembolso de {_reais(args['valor'])} foi aprovado.", "aprovada")


def recusar(atendimento: Atendimento, motivo: str) -> Atendimento:
    pend = _pendencia_ou_erro(atendimento)
    _encerrar_pendencia(pend, "recusada", motivo)
    return _fechar(atendimento, "escalado",
                   "Não foi possível aprovar o reembolso. Encaminhamos seu caso para um atendente.", "recusada")


def _encerrar_pendencia(pend: dict[str, Any], resolucao: str, motivo: str) -> None:
    arm = Armazem.atual()
    arm.con.execute("UPDATE pendencias SET resolvida_em=?, resolucao=? WHERE id=?",
                    (relogio.agora().isoformat(), f"{resolucao}: {motivo}", pend["id"]))
    arm.con.commit()
    arm.inserir("tickets", cliente_id=pend["cliente_id"], motivo=motivo,
                resumo=f"pendência {pend['id']} {resolucao}", quando=relogio.agora().isoformat())


def expirar_pendencias() -> list[dict[str, Any]]:
    """Encerra, por prazo vencido, toda pendência aberta além de PRAZO_APROVACAO segundo o relógio."""
    expiradas = []
    for linha in Armazem.atual().linhas("pendencias"):
        if linha["resolvida_em"] is None and relogio.agora() - __import__("datetime").datetime.fromisoformat(
            linha["criada_em"]) > PRAZO_APROVACAO:
            _encerrar_pendencia(linha, "expirada", "prazo vencido")
            expiradas.append(linha)
    return expiradas


def reiniciar_runner(atendimento: Atendimento) -> None:
    """Simula queda do processo: descarta runner e serviço de sessões. A fila de aprovação (armazém)
    sempre sobrevive; a conversa sobrevive só se a versão tem `persistencia` (SQLite)."""
    atendimento._servico = None
    atendimento._runner = None


def estado_persistido(atendimento: Atendimento) -> dict[str, Any] | None:
    """Estado da sessão lido direto do banco (só existe com `persistencia`). None se não há banco."""
    if atendimento._db is None:
        return None
    from google.adk.sessions.sqlite_session_service import SqliteSessionService
    try:
        servico = SqliteSessionService(db_path=atendimento._db)
        sessao = _rodar(lambda: servico.get_session(app_name=APP, user_id=atendimento.cliente_id,
                                                    session_id=atendimento.sessao_id))
        return dict(sessao.state) if sessao else None
    except Exception:
        return None
