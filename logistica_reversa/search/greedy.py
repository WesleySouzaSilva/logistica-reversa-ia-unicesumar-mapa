"""Busca Gulosa Melhor-Primeiro (Greedy Best-First Search).

Greedy expande o no com **menor valor de heuristica h(n)**,
ignorando o custo acumulado. Eh rapido e usa pouca memoria,
mas **nao eh otimo** em geral: uma heuristica enganadora pode
levar a solucoes arbitrariamente ruins.

A heuristica padrao eh a Manhattan (admissivel para grade
4-vizinhas). Pode ser substituida passando outra funcao com
a mesma assinatura.
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
    """Executa Greedy Best-First Search.

    Args:
        problem: `SearchProblem` com snapshot de goals.
        heuristic: funcao `(state, problem) -> float`. Padrao:
            `manhattan_heuristic`.

    Returns:
        O `SearchNode` de goal encontrado, ou None. **Nao
        garante otimalidade**.
    """
    if problem.is_goal_empty():
        return None

    if problem.goal_test(problem.initial_state):
        return SearchNode(state=problem.initial_state)

    counter = count()
    start = SearchNode(state=problem.initial_state)
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
            if child_state in explored:
                continue
            child = SearchNode(
                state=child_state,
                parent=node,
                action=str(child_state),
                path_cost=node.path_cost + problem.step_cost(node.state, child_state),
                depth=node.depth + 1,
            )
            heapq.heappush(
                frontier,
                (heuristic(child_state, problem), next(counter), child),
            )

    return None
