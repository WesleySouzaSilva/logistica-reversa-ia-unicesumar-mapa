"""Busca em Largura (Breadth-First Search).

BFS expande os nos em ordem de profundidade usando uma fila
(FIFO). Eh otimo quando todas as arestas tem o mesmo custo
(medido em hops), mas **ignora** os pesos das arestas: nao
confundir com UCS, que ordena pelo custo acumulado.

Algoritmo (Russell & Norvig, 3a ed., secao 3.4):
1. Enfileirar o no raiz.
2. Repetir: desenfileirar; se for goal, retornar; senao,
   enfileirar filhos nao explorados.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from logistica_reversa.domain.node import SearchNode
from logistica_reversa.search.problem import SearchProblem


def search(problem: SearchProblem) -> Optional[SearchNode[int]]:
    """Executa BFS a partir de `problem.initial_state`.

    Args:
        problem: `SearchProblem` com snapshot de goals.

    Returns:
        O `SearchNode` de goal, ou None se nao houver solucao
        (goals vazios, estado inicial nao alcancavel, etc.).
    """
    if problem.is_goal_empty():
        return None

    if problem.goal_test(problem.initial_state):
        return SearchNode(state=problem.initial_state)

    frontier: deque[SearchNode[int]] = deque(
        [SearchNode(state=problem.initial_state)]
    )
    explored: set[int] = set()

    while frontier:
        node = frontier.popleft()
        explored.add(node.state)

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
            if problem.goal_test(child_state):
                return child
            if child_state not in explored:
                frontier.append(child)

    return None
