"""Camada de agentes.

Define o contrato `BaseAgent` (inspirado em Russell & Norvig,
cap. 2) e a implementacao `ModelBasedAgent` usada pela
Questao 1.3 do MAPA. Outros tipos de agente (Simple-Reflex,
Goal-Based, Utility-Based) podem ser adicionados em PRs
futuros sem alterar esta interface.
"""
from logistica_reversa.agents.base import Action, BaseAgent
from logistica_reversa.agents.model_based import ModelBasedAgent

__all__ = ["Action", "BaseAgent", "ModelBasedAgent"]