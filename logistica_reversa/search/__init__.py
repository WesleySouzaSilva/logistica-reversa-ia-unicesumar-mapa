"""Camada de algoritmos de busca.

Implementa busca em grafo classica (classic graph search) sobre o
`Warehouse` da camada de ambiente, desacoplada do concreto atraves
de `SearchProblem`. Disponibiliza cinco algoritmos:

* BFS (Breadth-First Search) -- nao informado, otimo em hops.
* DFS (Depth-First Search) -- nao informado, nao otimo.
* UCS (Uniform-Cost Search) -- nao informado, otimo para custos >= 0.
* Greedy Best-First Search -- informado, nao otimo.
* A* -- informado, otimo quando a heuristica eh admissivel.
"""
from logistica_reversa.search.heuristics import (
    euclidean_heuristic,
    manhattan_heuristic,
)
from logistica_reversa.search.problem import (
    SearchProblem,
    build_problem_from_warehouse,
)
from logistica_reversa.search.astar import search as astar_search
from logistica_reversa.search.bfs import search as bfs_search
from logistica_reversa.search.dfs import search as dfs_search
from logistica_reversa.search.greedy import search as greedy_search
from logistica_reversa.search.ucs import search as ucs_search

__all__ = [
    "SearchProblem",
    "build_problem_from_warehouse",
    "manhattan_heuristic",
    "euclidean_heuristic",
    "bfs_search",
    "dfs_search",
    "ucs_search",
    "greedy_search",
    "astar_search",
]
