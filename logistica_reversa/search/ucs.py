"""Busca de Custo Uniforme (Uniform-Cost Search).

UCS eh o algoritmo de Dijkstra restrito a um estado inicial e
a um teste de objetivo. Expande os nos em ordem crescente de
**custo de caminho acumulado g(n)**. Eh otimo para arestas com
custo nao-negativo.

Tie-break: um contador monotono eh usado como chave secundaria
para garantir determinismo e evitar comparar `SearchNode` (que
nao implementa `__lt__`).
"""
from __future__ import annotations

import heapq
from itertools import count
from typing import Optional

from logistica_reversa.domain.node import SearchNode
from logistica_reversa.search.problem import SearchProblem


def search(problem: SearchProblem) -> Optional[SearchNode[int]]:
    """Executa UCS a partir de `problem.initial_state`.

    Args:
        problem: `SearchProblem` com snapshot de goals.

    Returns:
        O `SearchNode` de goal com menor `path_cost`, ou None
        se nao houver solucao.
    """
    if problem.is_goal_empty():
        return None

    if problem.goal_test(problem.initial_state):
        return SearchNode(state=problem.initial_state)

    counter = count()
    frontier: list[tuple[float, int, SearchNode[int]]] = [
        (0.0, next(counter), SearchNode(state=problem.initial_state))
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
            if child_state in explored:
                continue
            child = SearchNode(
                state=child_state,
                parent=node,
                action=str(child_state),
                path_cost=node.path_cost + problem.step_cost(node.state, child_state),
                depth=node.depth + 1,
            )
            heapq.heappush(frontier, (child.path_cost, next(counter), child))

    return None
