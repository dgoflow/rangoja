"""Roteiros de seção: respostas escritas à mão, para falhas induzidas (NB02, NB03).

Cada função recebe a Versao e devolve o roteiro com a forma certa (sequência ou agente único).
Ver `montar_roteiro`. São simulações do modelo, não gravações: as células dizem isso.
"""
from __future__ import annotations

from typing import Callable

from .modelo.roteiro import chamada, estruturada, texto
from .versoes import Versao


def triagem(categoria: str, pedido_id: str | None, problemas: list[str] | None = None,
            riscos: list[str] | None = None) -> dict:
    return {"categoria": categoria, "problemas": problemas or [categoria],
            "pedido_id": pedido_id, "sinais_de_risco": riscos or [], "resumo": "reclamação"}


def decisao(categoria: str, solucao: str, *, pedido_id: str | None = None, valor: float | None = None,
            problemas: list[str] | None = None, mensagem: str | None = None):
    return estruturada(categoria=categoria, problemas=problemas or [categoria], solucao=solucao,
                       valor=valor, pedido_id=pedido_id, justificativa="justificativa do modelo",
                       sinais_de_risco=[], mensagem_ao_cliente=mensagem)


def atendimento(versao: Versao, *, principal: list, triagem_passo: dict | None = None,
                resposta: str | None = None) -> dict:
    """Passos de UM atendimento para a versão dada (sequência ou agente único)."""
    if "sequencia" in versao:
        return {
            "triagem": [estruturada(**triagem_passo)] if triagem_passo else [],
            "resolucao": principal,
            "resposta": [texto(resposta or "Atualizamos o seu atendimento.")],
        }
    return {"unico": principal}


def montar_roteiro(*atendimentos: dict) -> dict:
    """Junta os passos de vários atendimentos, na ordem em que serão consumidos."""
    saida: dict[str, list] = {}
    for at in atendimentos:
        for agente, passos in at.items():
            saida.setdefault(agente, []).extend(passos)
    return saida


def n2_3_pii(v: Versao) -> dict:
    """C12: o modelo (simulado) cita nome e telefone do entregador. Simula regressão do contexto enxuto."""
    fala = "Ligue para o entregador Ricardo Fictício Souza no (00) 90000-1111."
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("indefinida", "5310"),
        principal=[decisao("indefinida", "nenhuma", pedido_id="5310", mensagem=fala)], resposta=fala))


def n2_5_desvio(v: Versao) -> dict:
    """C03: o modelo (simulado) reembolsa sem consultar o pedido."""
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("cobranca", "6002"),
        principal=[chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
                   decisao("cobranca", "reembolso", pedido_id="6002", valor=42.9)],
        resposta="Devolvemos R$ 42,90 da cobrança duplicada."))


def n2_6_golpe(v: Versao) -> dict:
    """C04: o modelo (simulado) tenta reembolsar um golpe antes de encaminhar à segurança."""
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("golpe", "7115", riscos=["golpe"]),
        principal=[chamada("registrar_reembolso", pedido_id="7115", valor=45.0, motivo="golpe"),
                   chamada("encaminhar_seguranca", pedido_id="7115", relato="pediu pagamento na maquininha"),
                   decisao("golpe", "encaminhar_seguranca", pedido_id="7115")],
        resposta="Encaminhamos seu relato à equipe de segurança."))


def n2_7_sem_pedido(v: Versao) -> dict:
    """C06: a triagem devolve pedido nulo e o modelo (simulado) decide mesmo assim."""
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("item_faltando", None),
        principal=[decisao("item_faltando", "reembolso", pedido_id=None, valor=30.0)],
        resposta="Reembolsamos R$ 30,00."))


def n3_2_ferramenta_fora(v: Versao) -> dict:
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("cobranca", "6002"),
        principal=[chamada("buscar_pedido", pedido_id="6002"),
                   chamada("escalar_para_humano", motivo="sistema indisponível", resumo="cobrança 6002"),
                   decisao("cobranca", "escalar_para_humano", pedido_id="6002")],
        resposta="Encaminhamos seu caso a um atendente."))


def n3_3_modelo(v: Versao) -> dict:
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("atraso", "5310"),
        principal=[chamada("buscar_pedido", pedido_id="5310"),
                   chamada("oferecer_cupom", pedido_id="5310", valor=10.0, motivo="atraso"),
                   decisao("atraso", "voucher", pedido_id="5310", valor=10.0)],
        resposta="Oferecemos um cupom de R$ 10 pelo atraso."))


def n3_4_loop(v: Versao) -> dict:
    buscas = [chamada("buscar_pedido", pedido_id="4821") for _ in range(4)]
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("item_faltando", "4821"),
        principal=buscas + [chamada("escalar_para_humano", motivo="resultado inconsistente", resumo="4821"),
                            decisao("item_faltando", "escalar_para_humano", pedido_id="4821")],
        resposta="Encaminhamos seu caso a um atendente."))


def n3_5_pendencia(v: Versao) -> dict:
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("item_faltando", "9001"),
        principal=[chamada("buscar_pedido", pedido_id="9001"),
                   chamada("registrar_reembolso", pedido_id="9001", valor=120.0, motivo="item_faltando"),
                   decisao("item_faltando", "reembolso", pedido_id="9001", valor=120.0)],
        resposta="Seu reembolso de R$ 120,00 está em análise."))


def n3_6_dobro(v: Versao) -> dict:
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("cobranca", "6002"),
        principal=[chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
                   chamada("registrar_reembolso", pedido_id="6002", valor=42.9, motivo="cobranca"),
                   decisao("cobranca", "reembolso", pedido_id="6002", valor=42.9)],
        resposta="Seu reembolso de R$ 42,90 foi registrado."))


def n3_0_feliz(v: Versao) -> dict:
    """C01 sem falha, para mostrar a anatomia de um trace."""
    return montar_roteiro(atendimento(
        v, triagem_passo=triagem("item_faltando", "4821", problemas=["item_faltando", "qualidade"]),
        principal=[chamada("buscar_pedido", pedido_id="4821"),
                   chamada("registrar_reembolso", pedido_id="4821", valor=8.0, motivo="item_faltando"),
                   decisao("item_faltando", "reembolso", pedido_id="4821", valor=8.0)],
        resposta="Reembolsamos R$ 8,00 do refrigerante."))


ROTEIROS: dict[str, Callable[[Versao], dict]] = {
    "N3.0": n3_0_feliz,
    "N2.3": n2_3_pii, "N2.5": n2_5_desvio, "N2.6": n2_6_golpe, "N2.7": n2_7_sem_pedido,
    "N3.1": n2_5_desvio, "N3.2": n3_2_ferramenta_fora, "N3.3": n3_3_modelo, "N3.4": n3_4_loop,
    "N3.5": n3_5_pendencia, "N3.6": n3_6_dobro,
}
