"""Enumeracoes centralizadas do dominio.

Reunir todos os enums em um unico modulo evita strings magicas
espalhadas e facilita a manutencao quando uma categoria nova
aparece (ex.: novo tipo de residuo ou novo algoritmo de busca).
"""
from __future__ import annotations

from enum import Enum


class WasteType(Enum):
    """Tipos de residuo coletados pelo agente.

    A escolha segue a classificacao basica da logistica reversa
    para fins didaticos. Valores estao em portugues para casar
    com a documentacao da atividade MAPA.
    """

    PLASTICO = "plastico"
    METAL = "metal"
    PAPEL = "papel"
    VIDRO = "vidro"
    ELETRONICO = "eletronico"


class AgentType(Enum):
    """Os quatro tipos de agente estudados em Russell & Norvig.

    - SIMPLE_REFLEX: reage apenas a percepcao atual.
    - MODEL_BASED: mantem estado interno (modelo do mundo).
    - GOAL_BASED: decide com base em objetivo explicito.
    - UTILITY_BASED: otimiza uma funcao de utilidade.
    """

    SIMPLE_REFLEX = "simple_reflex"
    MODEL_BASED = "model_based"
    GOAL_BASED = "goal_based"
    UTILITY_BASED = "utility_based"


class AlgorithmType(Enum):
    """Algoritmos de busca que serao comparados no PR #4."""

    BFS = "bfs"
    DFS = "dfs"
    UCS = "ucs"
    GREEDY = "greedy"
    ASTAR = "astar"
