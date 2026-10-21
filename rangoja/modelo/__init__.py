"""Pilha do modelo: fontes de resposta, injeção de falhas, retry e fallback."""
from .pilha import ModeloRangoja, RespostaAusente
from .roteiro import Roteiro, RoteiroEsgotado, chamada, estruturada, funcao, texto

__all__ = [
    "ModeloRangoja", "RespostaAusente", "Roteiro", "RoteiroEsgotado",
    "chamada", "estruturada", "funcao", "texto",
]
