"""Abstracao de problema de busca.

`SearchProblem` desacopla os algoritmos do `Warehouse` concreto:
toda busca recebe um problema e consome apenas `actions`, `step_cost`
e `goal_test`. Os goals sao capturados como **snapshot** na
construcao para que mutacoes posteriores do ambiente nao afetem
a busca em curso -- a mesma politica usada pela camada de
agentes (PR #5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from logistica_reversa.environment.warehouse import Warehouse


@dataclass(frozen=True)
class SearchProblem:
    """Problema de busca em grafo com estado em inteiros.

    Attributes:
        initial_state: id do setor onde a busca comeca.
        goals: ids dos setores objetivo, capturados como snapshot.
        warehouse: referencia ao `Warehouse` (usada por heuristicas
            e por `build_problem_from_warehouse` para injetar
            `actions`/`step_cost`). Algoritmos nao devem chamar
            metodos dele diretamente -- usem os callables.
        step_cost: `step_cost(a, b)` retorna o custo de ir de `a` para `b`.
        actions: `actions(state)` retorna os vizinhos de `state` ordenados.
    """

    initial_state: int
    goals: tuple[int, ...]
    warehouse: "Warehouse"
    step_cost: Callable[[int, int], float]
    actions: Callable[[int], list[int]]

    def goal_test(self, state: int) -> bool:
        """Retorna True se `state` eh um dos goals."""
        return state in self.goals

    def is_goal_empty(self) -> bool:
        """Retorna True quando o snapshot de goals esta vazio."""
        return len(self.goals) == 0

    def goal(self) -> int:
        """Retorna o unico goal.

        Raises:
            ValueError: se houver zero ou mais de um goal.
        """
        if len(self.goals) != 1:
            raise ValueError(
                f"goal() exige exatamente 1 goal, recebido {len(self.goals)}"
            )
        return self.goals[0]


def build_problem_from_warehouse(
    warehouse: "Warehouse",
    initial_state: int,
    goals: Optional[list[int]] = None,
) -> SearchProblem:
    """Constroi um `SearchProblem` a partir de um `Warehouse`.

    Args:
        warehouse: armazem a ser usado.
        initial_state: id do setor inicial.
        goals: lista de goals. Se None, captura
            `warehouse.sectors_with_waste()` como snapshot.

    Returns:
        Um `SearchProblem` com `actions` e `step_cost` injetados.
    """
    if goals is None:
        goals_snapshot = tuple(warehouse.sectors_with_waste())
    else:
        goals_snapshot = tuple(goals)

    return SearchProblem(
        initial_state=initial_state,
        goals=goals_snapshot,
        warehouse=warehouse,
        step_cost=lambda a, b: warehouse.edge_weight(a, b),
        actions=lambda state: warehouse.neighbors(state),
    )
