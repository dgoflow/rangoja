"""Montagem dos agentes a partir do conjunto de componentes de uma versão."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.run_config import RunConfig

from . import controle, dados, ferramentas
from .modelo import ModeloRangoja
from .tipos import Decisao, Triagem

NOME_RAIZ = "atendimento"
BASE = "Você atende clientes do RangoJá, um app de delivery. Responda em português, com cordialidade e objetividade."
INSTRUCAO_FERRAMENTAS = "Consulte os fatos com as ferramentas antes de decidir. Nunca invente valores de pedido."
# Só faz sentido com o componente `schema`: sem ele, o agente não tem decisão estruturada para entregar.
INSTRUCAO_SCHEMA = (
    "Sua resposta final é SEMPRE a decisão estruturada, nunca texto livre. Se faltar informação "
    "(ex.: o número do pedido) use categoria 'indefinida' e solucao 'pedir_informacao'; se o assunto "
    "não for do RangoJá use categoria 'fora_do_escopo' e solucao 'nenhuma'. Escreva o que o cliente "
    "deve ler em mensagem_ao_cliente."
)


def _politica_texto() -> str:
    return "\n\n".join(f"## {tema}\n{texto}" for tema, texto in dados.politica_secoes().items())


def _instrucao_unica(c: frozenset[str]) -> str:
    partes = [BASE]
    if "contexto_enxuto" not in c:
        partes.append("Política de atendimento:\n" + _politica_texto())
    else:
        partes.append("Consulte a política com `consultar_politica` quando precisar.")
    if "ferramentas" in c:  # com schema, o texto é o mesmo de antes da separação (uma frase seguida da outra)
        partes.append(INSTRUCAO_FERRAMENTAS + (" " + INSTRUCAO_SCHEMA if "schema" in c else ""))
    if "memoria_livre" in c:
        partes.append("Preferências e observações do cliente: {user:observacoes?}")
    if "memoria_segura" in c:
        partes.append("Preferências registradas do cliente: {user:preferencias?}")
    return "\n\n".join(partes)


def _fabrica_ferramentas(c: frozenset[str]) -> list[Any]:
    fs: list[Any] = []
    if "ferramentas" not in c:
        return fs
    fs.append(ferramentas._fabrica_buscar_pedido(enxuta="contexto_enxuto" in c))
    fs.append(ferramentas.consultar_politica)
    fs.append(ferramentas.oferecer_cupom)
    fs.append(ferramentas._fabrica_registrar_reembolso(
        idempotente="idempotencia" in c, com_aprovacao="aprovacao" in c))
    fs.append(ferramentas.solicitar_reenvio)
    fs.append(ferramentas.escalar_para_humano)
    fs.append(ferramentas.encaminhar_seguranca)
    if "memoria_livre" in c:
        fs.append(ferramentas.anotar_observacao)
    if "memoria_segura" in c:
        fs.append(ferramentas.registrar_preferencia)
    return fs


def _modelo(nome: str, c: frozenset[str]) -> ModeloRangoja:
    retry = "retry" in c
    fallback = ModeloRangoja(agente=nome, papel="secundario", retry=retry) if "fallback" in c else None
    return ModeloRangoja(agente=nome, papel="primario", retry=retry, fallback=fallback)


def _callbacks_modelo_entrada(c: frozenset[str]) -> list[Any]:
    return [controle.guardrail_entrada] if "guardrail_entrada" in c else []


def _callbacks_ferramenta(c: frozenset[str], com_categoria: bool) -> dict[str, Any]:
    antes = []
    if com_categoria and "categorias" in c:
        antes.append(controle.categorias_ferramenta)
    if "memoria_segura" in c:
        antes.append(controle.recorrencia_ferramenta)
    if "limites" in c:
        antes.append(controle.limite_ferramenta)
    out: dict[str, Any] = {}
    if antes:
        out["before_tool_callback"] = antes
    if "erros_estruturados" in c:
        out["on_tool_error_callback"] = controle.erro_estruturado
    return out


@dataclass
class Construida:
    agente_raiz: Any
    run_config: RunConfig
    componentes: frozenset[str]


def construir(c: frozenset[str]) -> Construida:
    run_config = RunConfig(max_llm_calls=20 if "limites" in c else 500)
    ferr = _fabrica_ferramentas(c)
    if "sequencia" not in c:
        agente = LlmAgent(
            name="unico",
            model=_modelo("unico", c),
            instruction=_instrucao_unica(c),
            tools=ferr,
            output_schema=Decisao if "schema" in c else None,
            output_key="decisao" if "schema" in c else "resposta",
            before_model_callback=_callbacks_modelo_entrada(c) or None,
            after_model_callback=controle.guardrail_saida if "guardrail_saida" in c else None,
            **_callbacks_ferramenta(c, com_categoria=False),
        )
        return Construida(agente, run_config, c)

    triagem = LlmAgent(
        name="triagem",
        model=_modelo("triagem", c),
        instruction=(
            "Classifique a reclamação: categoria principal, lista de problemas, pedido_id "
            "(ou null se não informado), sinais de risco e um resumo curto."
        ),
        output_schema=Triagem,
        output_key="triagem",
        before_model_callback=_callbacks_modelo_entrada(c) or None,
    )
    resolucao_cb: dict[str, Any] = {
        "before_model_callback": [controle.categorias_modelo] if "categorias" in c else None,
        "before_agent_callback": (controle.resolucao_antes if "contrato" in c else controle.consulta_deterministica),
        "after_agent_callback": controle.garantir_golpe if "categorias" in c else None,
    }
    resolucao = LlmAgent(
        name="resolucao",
        model=_modelo("resolucao", c),
        instruction=(
            "Com a triagem em {triagem?}, decida a solução permitida usando as ferramentas. "
            + INSTRUCAO_FERRAMENTAS + " " + INSTRUCAO_SCHEMA
        ),
        tools=ferr,
        output_schema=Decisao,
        output_key="decisao",
        **{k: v for k, v in resolucao_cb.items() if v is not None},
        **_callbacks_ferramenta(c, com_categoria=True),
    )
    resposta = LlmAgent(
        name="resposta",
        model=_modelo("resposta", c),
        instruction=(
            "Escreva a mensagem ao cliente, em português, com base na decisão em {decisao?}. "
            "Não mencione dados de entregadores."
        ),
        output_key="resposta",
        before_agent_callback=controle.contrato_resposta if "contrato" in c else None,
        after_model_callback=controle.guardrail_saida if "guardrail_saida" in c else None,
    )
    raiz = SequentialAgent(name=NOME_RAIZ, sub_agents=[triagem, resolucao, resposta])
    return Construida(raiz, run_config, c)
