"""Modelos puros do dominio.

Esta camada nao depende de nenhum outro modulo do projeto. Agentes,
buscas, servicos e visualizacao importam daqui -- nunca o contrario.
"""
from logistica_reversa.domain.enums import AgentType, AlgorithmType, WasteType
from logistica_reversa.domain.waste import Waste
from logistica_reversa.domain.sector import Sector
from logistica_reversa.domain.agent_state import AgentState
from logistica_reversa.domain.node import SearchNode

__all__ = [
    "AgentType",
    "AlgorithmType",
    "WasteType",
    "Waste",
    "Sector",
    "AgentState",
    "SearchNode",
]
