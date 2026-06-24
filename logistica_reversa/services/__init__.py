"""Camada de servicos: orquestracao entre agentes, ambiente e busca.

O loop principal de simulacao fica aqui. Mantem os agentes livres de
qualquer dependencia da estrutura do loop (eles recebem uma acao por
chamada de act()) e isola a politica de parada, o passo do relogio do
ambiente e o registro de metricas.
"""
from logistica_reversa.services.simulation import (
    Simulation,
    SimulationConfig,
    SimulationResult,
    StepRecord,
)

__all__ = [
    "Simulation",
    "SimulationConfig",
    "SimulationResult",
    "StepRecord",
]
