"""Testes da camada de busca.

Cobre a abstracao `SearchProblem`, as duas heuristicas
espaciais e os cinco algoritmos (BFS, DFS, UCS, Greedy, A*).
"""
from __future__ import annotations

import math

import pytest

from logistica_reversa.domain import Waste, WasteType
from logistica_reversa.environment import generate_grid_warehouse
from logistica_reversa.environment.warehouse import Warehouse
from logistica_reversa.search import (
    SearchProblem,
    astar_search,
    bfs_search,
    build_problem_from_warehouse,
    dfs_search,
    euclidean_heuristic,
    greedy_search,
    manhattan_heuristic,
    ucs_search,
)
from logistica_reversa.search.heuristics import manhattan_heuristic as _manhattan_aliased


# ---------- Helpers ----------


def _build_warehouse_with_waste(
    rows: int = 3,
    cols: int = 3,
    waste_ids: tuple[int, ...] = (8,),
) -> object:
    """Constroi um armazem em grade e deposita residuos nas celulas alvo."""
    wh = generate_grid_warehouse(rows, cols)
    for sid in waste_ids:
        wh.get_sector(sid).deposit(Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
    return wh


def _make_problem(wh, initial: int, goals: list[int] | None = None):
    return build_problem_from_warehouse(wh, initial_state=initial, goals=goals)


def _isolate_node(wh, node: int) -> None:
    """Remove todas as arestas conectando `node` ao resto do grafo."""
    for neighbor in list(wh.neighbors(node)):
        wh.graph.remove_edge(node, neighbor)


# ---------- TestSearchProblem ----------


class TestSearchProblem:
    def test_snapshot_captures_goals_at_construction(self):
        wh = _build_warehouse_with_waste(waste_ids=(7,))
        problem = _make_problem(wh, initial=0)
        assert problem.goals == (7,)
        wh.deposit_waste(8, Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
        assert problem.goals == (7,)

    def test_goal_test_true_for_goal(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        problem = _make_problem(wh, initial=0)
        assert problem.goal_test(5) is True

    def test_goal_test_false_for_non_goal(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        problem = _make_problem(wh, initial=0)
        assert problem.goal_test(3) is False

    def test_actions_match_neighbors(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=4)
        assert problem.actions(4) == wh.neighbors(4)

    def test_step_cost_matches_edge_weight(self):
        wh = generate_grid_warehouse(3, 3, edge_weight=2.5)
        problem = _make_problem(wh, initial=0, goals=[1])
        assert problem.step_cost(0, 1) == 2.5

    def test_empty_goals_marks_problem_unsolvable(self):
        wh = generate_grid_warehouse(3, 3)
        problem = _make_problem(wh, initial=0, goals=[])
        assert problem.is_goal_empty() is True

    def test_single_goal_helper(self):
        wh = _build_warehouse_with_waste(waste_ids=(4,))
        problem = _make_problem(wh, initial=0)
        assert problem.goal() == 4

    def test_single_goal_helper_raises_on_multiple(self):
        wh = _build_warehouse_with_waste(waste_ids=(4, 8))
        problem = _make_problem(wh, initial=0)
        with pytest.raises(ValueError):
            problem.goal()


# ---------- TestHeuristics ----------


class TestHeuristics:
    def test_manhattan_zero_for_same_state(self):
        wh = _build_warehouse_with_waste(waste_ids=(4,))
        problem = _make_problem(wh, initial=0)
        assert manhattan_heuristic(4, problem) == 0.0

    def test_manhattan_one_for_grid_neighbor(self):
        wh = _build_warehouse_with_waste(waste_ids=(1,))
        problem = _make_problem(wh, initial=0)
        assert manhattan_heuristic(0, problem) == 1.0

    def test_manhattan_diagonal_is_four(self):
        # Em grade 3x3: id 0 = (x=0, y=0), id 8 = (x=2, y=2).
        # Manhattan = |0 - 2| + |0 - 2| = 4.
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        assert manhattan_heuristic(0, problem) == 4.0

    def test_euclidean_diagonal_is_sqrt8(self):
        # Em grade 3x3: id 0 = (0, 0), id 8 = (2, 2). Dist = sqrt(4 + 4) = sqrt(8).
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        assert euclidean_heuristic(0, problem) == pytest.approx(math.sqrt(8.0))

    def test_min_over_multiple_goals(self):
        wh = _build_warehouse_with_waste(waste_ids=(2, 6))
        problem = _make_problem(wh, initial=0)
        # min(|0-0|+|0-2|, |0-2|+|0-1|) = min(2, 3) = 2
        assert manhattan_heuristic(0, problem) == 2.0

    def test_manhattan_aliased_import_works(self):
        assert _manhattan_aliased is manhattan_heuristic


# ---------- TestBFS ----------


class TestBFS:
    def test_finds_goal_when_in_initial_state(self):
        wh = _build_warehouse_with_waste(waste_ids=(0,))
        problem = _make_problem(wh, initial=0)
        node = bfs_search(problem)
        assert node is not None
        assert node.state == 0
        assert node.path_cost == 0.0
        assert node.depth == 0

    def test_shortest_in_edges_unweighted(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = bfs_search(problem)
        assert node is not None
        # caminho 0 -> 1 -> 2 -> 5 -> 8 tem 4 arestas (5 nos)
        assert len(node.path()) == 5

    def test_does_not_revisit_nodes(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = bfs_search(problem)
        assert node is not None
        states = [n.state for n in node.path()]
        assert len(states) == len(set(states))

    def test_returns_none_when_no_path_isolated(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        # cria goal em componente separado (mas ainda adjacente via grade)
        # Truque: deposita em 5 mas remove a aresta que conecta 5 ao resto
        _isolate_node(wh, 5)
        problem = _make_problem(wh, initial=0)
        node = bfs_search(problem)
        assert node is None

    def test_ignores_edge_weight(self):
        wh = generate_grid_warehouse(3, 3, edge_weight=5.0)
        wh.get_sector(8).deposit(Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
        problem = _make_problem(wh, initial=0)
        node = bfs_search(problem)
        # BFS ignora o peso; o numero de hops eh 4
        assert node is not None
        assert len(node.path()) == 5
        assert node.path_cost == pytest.approx(4 * 5.0)

    def test_returns_none_when_empty_goals(self):
        wh = generate_grid_warehouse(3, 3)
        problem = _make_problem(wh, initial=0, goals=[])
        assert bfs_search(problem) is None


# ---------- TestDFS ----------


class TestDFS:
    def test_finds_a_goal(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = dfs_search(problem)
        assert node is not None
        assert problem.goal_test(node.state)

    def test_iterative_no_recursion_error(self):
        wh = _build_warehouse_with_waste(rows=10, cols=10, waste_ids=(99,))
        problem = _make_problem(wh, initial=0)
        # Nao deve levantar RecursionError
        node = dfs_search(problem)
        assert node is not None
        assert problem.goal_test(node.state)

    def test_returns_none_when_no_path(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        _isolate_node(wh, 5)
        problem = _make_problem(wh, initial=0)
        assert dfs_search(problem) is None

    def test_does_not_loop(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = dfs_search(problem)
        assert node is not None
        states = [n.state for n in node.path()]
        assert len(states) == len(set(states))


# ---------- TestUCS ----------


class TestUCS:
    def test_optimal_path_in_weighted_grid(self):
        # 3x3: 0 -- 1 -- 2
        #      |         |
        #      3 -- 4 -- 5
        #      |         |
        #      6 -- 7 -- 8
        # Atribui peso 1.0 nas horizontais, 10.0 nas verticais
        wh = generate_grid_warehouse(3, 3, edge_weight=1.0)
        for r in range(2):
            for c in range(3):
                a = r * 3 + c
                b = (r + 1) * 3 + c
                wh.add_edge(a, b, weight=10.0)
        wh.get_sector(8).deposit(Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
        problem = _make_problem(wh, initial=0)
        node = ucs_search(problem)
        assert node is not None
        # Otimo: 0->1->2->5->8: 2 verticais (10.0) + 2 horizontais (1.0) = 22.0
        # (qualquer caminho de 0 a 8 exige ao menos 2 descidas verticais)
        assert node.path_cost == pytest.approx(22.0)
        states = [n.state for n in node.path()]
        assert states == [0, 1, 2, 5, 8]

    def test_returns_none_for_unreachable(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        _isolate_node(wh, 5)
        problem = _make_problem(wh, initial=0)
        assert ucs_search(problem) is None

    def test_uniform_weights_matches_bfs_hops(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = ucs_search(problem)
        assert node is not None
        # custo == profundidade em grade uniforme
        assert node.path_cost == node.depth

    def test_deterministic_on_ties(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        n1 = ucs_search(problem)
        n2 = ucs_search(problem)
        assert [x.state for x in n1.path()] == [x.state for x in n2.path()]

    def test_returns_none_when_empty_goals(self):
        wh = generate_grid_warehouse(3, 3)
        problem = _make_problem(wh, initial=0, goals=[])
        assert ucs_search(problem) is None


# ---------- TestGreedy ----------


class TestGreedy:
    def test_finds_goal(self):
        wh = _build_warehouse_with_waste(waste_ids=(1,))
        problem = _make_problem(wh, initial=0)
        node = greedy_search(problem)
        assert node is not None
        assert problem.goal_test(node.state)

    def test_not_optimal_obstacle_demo(self):
        # Grade 2x4 em "L" improvisado: 0 -- 1 -- 2 -- 3
        #                                 |
        #                                 4 -- 5 -- 6 -- 7
        # Goal em 7. Custo uniforme.
        # Greedy vai direto: 0->1->2->3->7 (custo 4) ou 0->4->5->6->7 (custo 4)
        # Em grade uniforme ambos sao otimos. Para forcar a nao-otimalidade
        # vamos usar custo desigual.
        wh = generate_grid_warehouse(2, 4, edge_weight=1.0)
        # Aumenta custo da rota "cima" (horizontal 0-1-2-3)
        for a, b in [(0, 1), (1, 2), (2, 3)]:
            wh.add_edge(a, b, weight=10.0)
        wh.get_sector(7).deposit(Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
        problem = _make_problem(wh, initial=0)
        node = greedy_search(problem)
        # Greedy sobe: 0->1 (h=3) -> 2 (h=2) -> 3 (h=1) -> 7 (h=0)
        # Custo 30. Otimo real: 0->4->5->6->7 com custo 4
        assert node is not None
        assert node.path_cost > ucs_search(problem).path_cost

    def test_uses_manhattan_by_default(self):
        wh = _build_warehouse_with_waste(waste_ids=(1,))
        problem = _make_problem(wh, initial=0)
        node = greedy_search(problem)
        # Com heuristica Manhattan, em grade simples sem obstaculos,
        # o caminho retornado deve ter custo == profundidade.
        assert node is not None
        assert node.path_cost == node.depth

    def test_returns_none_when_unreachable(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        _isolate_node(wh, 5)
        problem = _make_problem(wh, initial=0)
        assert greedy_search(problem) is None


# ---------- TestAStar ----------


class TestAStar:
    def test_optimal_path_simple_grid(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = astar_search(problem)
        assert node is not None
        assert node.path_cost == pytest.approx(4.0)
        assert node.depth == 4

    def test_optimal_with_weighted_edges(self):
        wh = generate_grid_warehouse(3, 3, edge_weight=1.0)
        for r in range(2):
            for c in range(3):
                a = r * 3 + c
                b = (r + 1) * 3 + c
                wh.add_edge(a, b, weight=10.0)
        wh.get_sector(8).deposit(Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0))
        problem = _make_problem(wh, initial=0)
        node = astar_search(problem)
        assert node is not None
        assert node.path_cost == pytest.approx(22.0)
        assert [n.state for n in node.path()] == [0, 1, 2, 5, 8]

    def test_admissible_heuristic_returns_optimal(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        a_node = astar_search(problem)
        u_node = ucs_search(problem)
        assert a_node.path_cost == pytest.approx(u_node.path_cost)

    def test_euclidean_also_optimal_on_grid(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = astar_search(problem, heuristic=euclidean_heuristic)
        u_node = ucs_search(problem)
        assert node.path_cost == pytest.approx(u_node.path_cost)

    def test_returns_none_when_empty_goals(self):
        wh = generate_grid_warehouse(3, 3)
        problem = _make_problem(wh, initial=0, goals=[])
        assert astar_search(problem) is None

    def test_returns_none_when_unreachable(self):
        wh = _build_warehouse_with_waste(waste_ids=(5,))
        _isolate_node(wh, 5)
        problem = _make_problem(wh, initial=0)
        assert astar_search(problem) is None


# ---------- TestAlgorithmAgreement ----------


class TestAlgorithmAgreement:
    def test_bfs_ucs_astar_share_optimal_cost_uniform(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        b = bfs_search(problem)
        u = ucs_search(problem)
        a = astar_search(problem)
        # Em grade uniforme, BFS (hops) == UCS (custo) == A* (custo)
        assert b.depth == u.path_cost == a.path_cost

    def test_all_algorithms_return_none_on_empty_goals(self):
        wh = generate_grid_warehouse(3, 3)
        problem = _make_problem(wh, initial=0, goals=[])
        assert bfs_search(problem) is None
        assert dfs_search(problem) is None
        assert ucs_search(problem) is None
        assert greedy_search(problem) is None
        assert astar_search(problem) is None

    def test_returns_search_node_with_path(self):
        wh = _build_warehouse_with_waste(waste_ids=(8,))
        problem = _make_problem(wh, initial=0)
        node = astar_search(problem)
        path = node.path()
        assert path[0].state == 0
        assert path[-1].state == 8
        # Cada no filho deve ter como parent o anterior
        for prev, curr in zip(path, path[1:]):
            assert curr.parent is prev
