"""Ferramentas do agente. Efeitos vão para o armazém; estado da conversa vai para tool_context.state.

Cada ferramenta começa chamando `falhas.na_ferramenta`, que pode lançar a falha injetada.
As variantes (buscar_pedido enxuta/completa, registrar_reembolso com/sem idempotência,
memória livre/segura) são escolhidas pelos componentes da versão, em agentes.py.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

from google.adk.tools.tool_context import ToolContext

from . import dados, falhas, politica, relogio
from .armazem import Armazem
from .tipos import Pedido


def _falhou(mensagem: str, **extra: Any) -> dict[str, Any]:
    return {"erro": mensagem, **extra}


def _pedido_ou_erro(pedido_id: str) -> tuple[Pedido | None, dict[str, Any] | None]:
    pedido = dados.pedido(pedido_id)
    if pedido is None:
        return None, _falhou("pedido_inexistente", pedido_id=pedido_id)
    return pedido, None


def _ambiguo(nome: str) -> dict[str, Any] | None:
    if falhas.ferramenta_ambigua(nome):
        return {"status": "incompleto", "mensagem": "resultado incompleto, tente de novo"}
    return None


def _resumo_enxuto(pedido: Pedido) -> dict[str, Any]:
    """Só o necessário para decidir: sem endereço, sem dados do entregador (N1.6)."""
    return {
        "pedido_id": pedido.pedido_id,
        "restaurante": pedido.restaurante,
        "itens": [i.model_dump(mode="json") for i in pedido.itens],
        "taxa_entrega": str(pedido.taxa_entrega),
        "total": str(pedido.total),
        "pagamentos": [p.model_dump(mode="json") for p in pedido.pagamentos],
        "atraso_minutos": politica.atraso_minutos(pedido),
        "status": pedido.status,
    }


def _completo(pedido: Pedido) -> dict[str, Any]:
    """Pedido inteiro, com o entregador embutido. É a versão que vaza PII (falha de N1.6)."""
    dump = pedido.model_dump(mode="json")
    entregador = dados.entregador(pedido.entregador_id)
    dump["entregador"] = entregador.model_dump(mode="json") if entregador else None
    dump["atraso_minutos"] = politica.atraso_minutos(pedido)
    return dump


def _fabrica_buscar_pedido(enxuta: bool):
    def buscar_pedido(pedido_id: str, tool_context: ToolContext) -> dict[str, Any]:
        """Consulta um pedido pelo número. Devolve itens, valores, pagamentos e atraso."""
        falhas.na_ferramenta("buscar_pedido")
        if (r := _ambiguo("buscar_pedido")) is not None:
            return r
        pedido, erro = _pedido_ou_erro(pedido_id)
        if erro:
            return erro
        tool_context.state["pedido_id"] = pedido_id
        return _resumo_enxuto(pedido) if enxuta else _completo(pedido)

    buscar_pedido.__name__ = "buscar_pedido"
    return buscar_pedido


def consultar_politica(tema: str) -> dict[str, Any]:
    """Consulta um trecho da política de atendimento. Temas: categorias, item_faltando, item_errado, cobranca, atraso, qualidade, golpe, limites, recorrencia, privacidade, memoria, fora_do_escopo."""
    falhas.na_ferramenta("consultar_politica")
    secoes = dados.politica_secoes()
    if tema not in secoes:
        return {"erro": "tema_inexistente", "temas": sorted(secoes)}
    return {"tema": tema, "texto": secoes[tema]}


def oferecer_cupom(pedido_id: str, valor: float, motivo: str, tool_context: ToolContext) -> dict[str, Any]:
    """Oferece um cupom de desconto ao cliente. Até R$ 15 por atendimento."""
    falhas.na_ferramenta("oferecer_cupom")
    if Decimal(str(valor)) > politica.CUPOM_MAX:
        return _falhou("valor_acima_do_cupom_maximo", maximo=str(politica.CUPOM_MAX))
    pedido, erro = _pedido_ou_erro(pedido_id)
    if erro:
        return erro
    cupom_id = Armazem.atual().inserir(
        "cupons", pedido_id=pedido_id, cliente_id=pedido.cliente_id, valor=str(valor),
        motivo=motivo, quando=relogio.agora().isoformat(),
    )
    tool_context.state["compensacoes"] = float(tool_context.state.get("compensacoes", 0)) + float(valor)
    return {"cupom_id": cupom_id, "valor": valor, "status": "oferecido"}


def efetivar_reembolso(pedido_id: str, valor: float, motivo: str, *, idempotente: bool) -> dict[str, Any]:
    """Efeito do reembolso no sistema. Usado pela ferramenta e, após aprovação humana, por execucao.aprovar."""
    falhas.na_ferramenta("registrar_reembolso")
    pedido, erro = _pedido_ou_erro(pedido_id)
    if erro:
        return erro
    if Decimal(str(valor)) <= 0 or Decimal(str(valor)) > pedido.total:
        return _falhou("valor_invalido", total_do_pedido=str(pedido.total))
    chave = f"{pedido_id}:{motivo.strip().lower()}" if idempotente else None
    if chave is not None:
        existente = Armazem.atual().reembolso_por_chave(chave)
        if existente is not None:
            return {"reembolso_id": existente["id"], "valor": float(existente["valor"]), "status": "ja_registrado"}
    rid = Armazem.atual().inserir(
        "reembolsos", pedido_id=pedido_id, cliente_id=pedido.cliente_id, valor=str(valor),
        motivo=motivo, chave=chave, quando=relogio.agora().isoformat(), origem="sistema",
    )
    falhas.apos_efeito("registrar_reembolso")
    return {"reembolso_id": rid, "valor": valor, "status": "registrado"}


def _registrar(pedido_id: str, valor: float, motivo: str, tool_context: ToolContext,
               idempotente: bool, com_aprovacao: bool) -> dict[str, Any]:
    falhas.na_ferramenta("registrar_reembolso")
    if com_aprovacao and politica.precisa_aprovacao(valor):
        pedido, erro = _pedido_ou_erro(pedido_id)
        if erro:
            return erro
        pid = Armazem.atual().inserir(
            "pendencias", sessao_id=str(tool_context.state.get("sessao_id", "")),
            cliente_id=pedido.cliente_id, chamada_id=uuid.uuid4().hex, ferramenta="registrar_reembolso",
            args_json=json.dumps({"pedido_id": pedido_id, "valor": valor, "motivo": motivo}),
            criada_em=relogio.agora().isoformat(), resolvida_em=None, resolucao=None,
        )
        tool_context.state["status"] = "aguardando_aprovacao"
        return {
            "status": "aguardando_aprovacao",
            "pendencia_id": pid,
            "mensagem": "valor acima do limite automático; enviado para aprovação humana",
        }
    resultado = efetivar_reembolso(pedido_id, valor, motivo, idempotente=idempotente)
    if resultado.get("status") in ("registrado", "ja_registrado"):
        tool_context.state["compensacoes"] = float(tool_context.state.get("compensacoes", 0)) + float(valor)
        tool_context.state["reembolsado"] = True
    return resultado


def _fabrica_registrar_reembolso(idempotente: bool, com_aprovacao: bool = False):
    def registrar_reembolso(pedido_id: str, valor: float, motivo: str, tool_context: ToolContext) -> dict[str, Any]:
        """Registra o reembolso de um pedido. Ação irreversível: informe o motivo (ex.: item_faltando, cobranca)."""
        return _registrar(pedido_id, valor, motivo, tool_context, idempotente, com_aprovacao)

    registrar_reembolso.__name__ = "registrar_reembolso"
    return registrar_reembolso


def solicitar_reenvio(pedido_id: str, item: str, tool_context: ToolContext) -> dict[str, Any]:
    """Solicita o reenvio de um item que veio errado."""
    falhas.na_ferramenta("solicitar_reenvio")
    _, erro = _pedido_ou_erro(pedido_id)
    if erro:
        return erro
    rid = Armazem.atual().inserir("reenvios", pedido_id=pedido_id, item=item, quando=relogio.agora().isoformat())
    return {"reenvio_id": rid, "status": "solicitado"}


def escalar_para_humano(motivo: str, resumo: str, tool_context: ToolContext) -> dict[str, Any]:
    """Encaminha o atendimento para um atendente humano, com um resumo do caso."""
    falhas.na_ferramenta("escalar_para_humano")
    tid = Armazem.atual().inserir(
        "tickets", cliente_id=str(tool_context.state.get("cliente_id", "")), motivo=motivo,
        resumo=resumo, quando=relogio.agora().isoformat(),
    )
    tool_context.state["status"] = "escalado"
    return {"ticket_id": tid, "status": "escalado"}


def encaminhar_seguranca(pedido_id: str, relato: str, tool_context: ToolContext) -> dict[str, Any]:
    """Encaminha um relato de golpe ou fraude à equipe de segurança. Não gera compensação."""
    falhas.na_ferramenta("encaminhar_seguranca")
    protocolo = Armazem.atual().inserir(
        "seguranca", pedido_id=pedido_id, cliente_id=str(tool_context.state.get("cliente_id", "")),
        relato=relato, quando=relogio.agora().isoformat(),
    )
    tool_context.state["status"] = "encaminhado_seguranca"
    return {"protocolo": protocolo, "status": "encaminhado"}


def anotar_observacao(texto: str, tool_context: ToolContext) -> dict[str, Any]:
    """Anota uma observação livre sobre o cliente para atendimentos futuros. Use com cuidado."""
    falhas.na_ferramenta("anotar_observacao")
    obs = list(tool_context.state.get("user:observacoes", []))
    obs.append(texto)
    tool_context.state["user:observacoes"] = obs
    return {"ok": True}


def registrar_preferencia(campo: str, valor: str, tool_context: ToolContext) -> dict[str, Any]:
    """Registra uma preferência de entrega do cliente. Campos: local_entrega, canal_contato, horario_preferido."""
    falhas.na_ferramenta("registrar_preferencia")
    if campo not in politica.CAMPOS_PREFERENCIA:
        return _falhou("campo_nao_permitido", permitidos=sorted(politica.CAMPOS_PREFERENCIA))
    prefs = dict(tool_context.state.get("user:preferencias", {}))
    prefs[campo] = valor
    tool_context.state["user:preferencias"] = prefs
    return {"ok": True, "campo": campo}


FERRAMENTAS_SEM_VARIANTE = {
    "consultar_politica": consultar_politica,
    "oferecer_cupom": oferecer_cupom,
    "solicitar_reenvio": solicitar_reenvio,
    "escalar_para_humano": escalar_para_humano,
    "encaminhar_seguranca": encaminhar_seguranca,
    "anotar_observacao": anotar_observacao,
    "registrar_preferencia": registrar_preferencia,
}
