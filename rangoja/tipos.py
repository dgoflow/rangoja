"""Modelos do domínio. Valores monetários em Decimal; horários com fuso."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

Categoria = Literal[
    "item_faltando", "item_errado", "cobranca", "atraso", "qualidade",
    "golpe", "fora_do_escopo", "indefinida",
]

Solucao = Literal[
    "reembolso", "voucher", "voucher_e_reembolso_taxa", "reenvio",
    "encaminhar_seguranca", "escalar_para_humano", "nenhuma", "pedir_informacao",
]

Status = Literal[
    "concluido", "aguardando_cliente", "aguardando_aprovacao", "escalado",
    "encaminhado_seguranca", "erro",
]


class Item(BaseModel):
    nome: str
    qtd: int
    preco: Decimal
    entregue: bool = True


class Pagamento(BaseModel):
    valor: Decimal
    quando: datetime


class Horarios(BaseModel):
    pedido: datetime
    prometido: datetime
    entregue: Optional[datetime] = None


class Pedido(BaseModel):
    pedido_id: str
    cliente_id: str
    restaurante: str
    itens: list[Item]
    taxa_entrega: Decimal
    total: Decimal
    pagamentos: list[Pagamento]
    horarios: Horarios
    status: Literal["entregue", "em_rota", "cancelado"]
    entregador_id: str


class Entregador(BaseModel):
    entregador_id: str
    nome_completo: str
    telefone: str
    placa: str


class ReembolsoHistorico(BaseModel):
    pedido_id: str
    valor: Decimal
    quando: datetime


class Cliente(BaseModel):
    cliente_id: str
    nome: str
    reembolsos: list[ReembolsoHistorico] = Field(default_factory=list)
    preferencias: dict[str, str] = Field(default_factory=dict)


class Triagem(BaseModel):
    """Saída do agente de triagem (primeira etapa da sequência)."""
    categoria: Categoria
    problemas: list[Categoria] = Field(default_factory=list)
    pedido_id: Optional[str] = None
    sinais_de_risco: list[str] = Field(default_factory=list)
    resumo: str = ""


class Decisao(BaseModel):
    """Decisão estruturada da resolução. É o contrato entre o modelo e o código."""
    categoria: Categoria
    problemas: list[Categoria] = Field(default_factory=list)
    solucao: Solucao
    # float e não Decimal: o ADK serializa a saída estruturada com json padrão (set_model_response)
    valor: Optional[float] = None
    pedido_id: Optional[str] = None
    justificativa: str = ""
    sinais_de_risco: list[str] = Field(default_factory=list)
    mensagem_ao_cliente: Optional[str] = None
