"""Heuristicas espaciais admissiveis para busca informada.

Ambas as heuristicas sao **admissiveis** para grades 4-vizinhas com
custo de aresta uniforme >= 1: a distancia real nao pode exceder
a distancia em linha reta. Sao wrappers finos sobre os metodos
metricos ja implementados em `Warehouse`, preservando a
consistencia com a coordenada (x, y) usada pelo gerador de grade.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logistica_reversa.environment.warehouse import Warehouse
    from logistica_reversa.search.problem import SearchProblem


def manhattan_heuristic(state: int, problem: "SearchProblem") -> float:
    """Heuristica de distancia de Manhattan ate o goal mais proximo.

    Args:
        state: id do setor atual.
        problem: `SearchProblem` com `warehouse` e `goals`.

    Returns:
        Manhattan(state, g) para o goal g mais proximo. 0.0 se
        `state` ja eh um goal ou se nao ha goals.
    """
    if problem.is_goal_empty():
        return 0.0
    warehouse: "Warehouse" = problem.warehouse
    return min(warehouse.manhattan(state, goal) for goal in problem.goals)


def euclidean_heuristic(state: int, problem: "SearchProblem") -> float:
    """Heuristica de distancia Euclidiana ate o goal mais proximo.

    Args:
        state: id do setor atual.
        problem: `SearchProblem` com `warehouse` e `goals`.

    Returns:
        Euclidiana(state, g) para o goal g mais proximo. 0.0 se
        `state` ja eh um goal ou se nao ha goals.
    """
    if problem.is_goal_empty():
        return 0.0
    warehouse: "Warehouse" = problem.warehouse
    return min(warehouse.euclidean(state, goal) for goal in problem.goals)
