"""Algoritmo A* (A-Estrela).

A* combina custo acumulado e heuristica pela funcao de
avaliacao **f(n) = g(n) + h(n)**, onde g(n) eh o custo
acumulado e h(n) eh a heuristica. Eh otimo sempre que h for
**admissivel** (nunca superestima o custo real ate um goal)
e a busca for em grafo classico (com `explored`/`g_score`).

A heuristica padrao eh a Manhattan, admissivel para grades
4-vizinhas com custo de aresta uniforme. Para multiplos goals,
a heuristica retorna o minimo das distancias ate cada goal
(ainda admissivel).
"""
from __future__ import annotations

import heapq
from itertools import count
from typing import Callable, Optional

from logistica_reversa.domain.node import SearchNode
from logistica_reversa.search.heuristics import manhattan_heuristic
from logistica_reversa.search.problem import SearchProblem


def search(
    problem: SearchProblem,
    heuristic: Callable[[int, SearchProblem], float] = manhattan_heuristic,
) -> Optional[SearchNode[int]]:
    """Executa A* sobre `problem`.

    Args:
        problem: `SearchProblem` com snapshot de goals.
        heuristic: funcao `(state, problem) -> float`. Padrao:
            `manhattan_heuristic`.

    Returns:
        O `SearchNode` de goal com menor custo total, ou None
        se nao houver solucao. Otimo quando a heuristica eh
        admissivel.
    """
    if problem.is_goal_empty():
        return None

    if problem.goal_test(problem.initial_state):
        return SearchNode(state=problem.initial_state)

    counter = count()
    start = SearchNode(state=problem.initial_state)
    g_score: dict[int, float] = {problem.initial_state: 0.0}
    frontier: list[tuple[float, int, SearchNode[int]]] = [
        (heuristic(problem.initial_state, problem), next(counter), start)
    ]
    explored: set[int] = set()

    while frontier:
        _, _, node = heapq.heappop(frontier)
        if node.state in explored:
            continue
        explored.add(node.state)

        if problem.goal_test(node.state):
            return node

        for action in problem.actions(node.state):
            child_state = action
            tentative_g = node.path_cost + problem.step_cost(node.state, child_state)
            if child_state in explored and tentative_g >= g_score.get(
                child_state, float("inf")
            ):
                continue
            if tentative_g < g_score.get(child_state, float("inf")):
                g_score[child_state] = tentative_g
                child = SearchNode(
                    state=child_state,
                    parent=node,
                    action=str(child_state),
                    path_cost=tentative_g,
                    depth=node.depth + 1,
                )
                f = tentative_g + heuristic(child_state, problem)
                heapq.heappush(frontier, (f, next(counter), child))

    return None
