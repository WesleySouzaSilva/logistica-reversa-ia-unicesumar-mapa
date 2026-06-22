"""No de busca generico.

SearchNode eh a estrutura usada por todos os algoritmos de busca
(BFS, DFS, UCS, Greedy, A*). Eh generico no tipo de estado para
reuso entre problemas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Optional, TypeVar

StateT = TypeVar("StateT")


@dataclass
class SearchNode(Generic[StateT]):
    """Um no na arvore de busca.

    Attributes:
        state: o estado que este no representa.
        parent: no pai, ou None se for raiz.
        action: acao que levou do estado do pai ate este estado.
        path_cost: custo acumulado desde a raiz ate este no.
        depth: profundidade na arvore de busca.
    """

    state: StateT
    parent: Optional["SearchNode[StateT]"] = field(default=None, repr=False)
    action: Optional[str] = field(default=None)
    path_cost: float = 0.0
    depth: int = 0

    def path(self) -> list["SearchNode[StateT]"]:
        """Reconstitui o caminho da raiz ate este no.

        Returns:
            Lista de nos da raiz ate este no (inclusivo).
        """
        node: Optional[SearchNode[StateT]] = self
        result: list[SearchNode[StateT]] = []
        while node is not None:
            result.append(node)
            node = node.parent
        result.reverse()
        return result
