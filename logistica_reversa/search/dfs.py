"""Busca em Profundidade (Depth-First Search).

DFS expande o no mais profundo da fronteira usando uma pilha
(LIFO). **Nao eh otimo** em geral e pode nao ser completo em
grafos com ciclos sem a protecao do conjunto `explored`.

Implementacao iterativa (pilha explicita) para nao estourar o
limite de recursao do Python em grades grandes.
"""
from __future__ import annotations

from typing import Optional

from logistica_reversa.domain.node import SearchNode
from logistica_reversa.search.problem import SearchProblem


def search(problem: SearchProblem) -> Optional[SearchNode[int]]:
    """Executa DFS iterativo a partir de `problem.initial_state`.

    Args:
        problem: `SearchProblem` com snapshot de goals.

    Returns:
        O `SearchNode` de goal, ou None se nao houver solucao.
        O caminho retornado **nao eh necessariamente otimo**.
    """
    if problem.is_goal_empty():
        return None

    if problem.goal_test(problem.initial_state):
        return SearchNode(state=problem.initial_state)

    frontier: list[SearchNode[int]] = [
        SearchNode(state=problem.initial_state)
    ]
    explored: set[int] = set()

    while frontier:
        node = frontier.pop()
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
            frontier.append(child)

    return None
