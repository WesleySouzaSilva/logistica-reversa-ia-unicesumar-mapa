"""Agente baseado em modelo (Model-Based Reflex Agent).

Implementa a Questao 1.3 do MAPA: um agente que mantem estado
interno (modelo do mundo), respeita uma regra anti-retorno
(via `AgentState.cooldown`) e usa um planejador da camada
`search/` para alcancar residuos distantes.

Algoritmo de `act` (um passo):

1. Se o setor atual tem residuo -> `COLLECT` (sem planejar).
2. Caso contrario, filtra os goals pela regra `can_return`.
   Se nenhum goal for alcancavel -> `WAIT`.
3. Constroi um `SearchProblem` com os goals filtrados e roda
   o planejador injetado (padrao: A* com heuristica Manhattan).
4. Se o planejador retorna None -> `WAIT`.
5. Caminha para o segundo no do caminho planejado -> `MOVE`.

Determinismo: o planejador padrao (A*) ja eh deterministico,
e `Warehouse.neighbors()` retorna lista ordenada, de modo que
duas chamadas identicas produzem o mesmo `last_move_target`.
"""
from __future__ import annotations

from typing import Callable, Optional

from logistica_reversa.agents.base import Action, BaseAgent
from logistica_reversa.domain.agent_state import AgentState
from logistica_reversa.environment.warehouse import Warehouse
from logistica_reversa.search import (
    astar_search,
    build_problem_from_warehouse,
    manhattan_heuristic,
)


class ModelBasedAgent(BaseAgent):
    """Agente baseado em modelo com planejador da camada `search/`.

    Attributes:
        state: estado interno do agente (mutado a cada `act`).
        last_action: ultima `Action` retornada por `act`.
        last_move_target: id do setor de destino da ultima `MOVE`,
            ou None se a ultima acao nao foi `MOVE`.
    """

    def __init__(
        self,
        warehouse: Warehouse,
        initial_sector: int,
        cooldown: int = 3,
        energy_per_step: float = 1.0,
        energy_per_collect: float = 0.5,
        planner: Callable = astar_search,
        heuristic: Callable[[int, object], float] = manhattan_heuristic,
    ) -> None:
        """Inicializa o agente.

        Args:
            warehouse: armazem a ser explorado. Usado para sensorear
                residuos e construir o `SearchProblem`.
            initial_sector: id do setor onde o agente comeca.
            cooldown: T passado a `AgentState` (passos minimos antes
                de retornar a um setor recem-limpo).
            energy_per_step: energia consumida por `MOVE`.
            energy_per_collect: energia consumida por `COLLECT`.
            planner: funcao `(SearchProblem, heuristic) -> SearchNode | None`.
            heuristic: heuristica espacial usada pelo planejador.

        Raises:
            ValueError: se consumos forem negativos.
        """
        if energy_per_step < 0:
            raise ValueError(
                f"energy_per_step deve ser >= 0, recebido {energy_per_step}"
            )
        if energy_per_collect < 0:
            raise ValueError(
                f"energy_per_collect deve ser >= 0, recebido {energy_per_collect}"
            )
        self._warehouse = warehouse
        self._planner = planner
        self._heuristic = heuristic
        self._energy_per_step = energy_per_step
        self._energy_per_collect = energy_per_collect
        self.state: AgentState = AgentState(
            current_sector=initial_sector,
            cooldown=cooldown,
        )
        self.last_action: Action = Action.WAIT
        self.last_move_target: Optional[int] = None

    # ---------- Percepção ----------

    def perceive(self, observation: list[int]) -> None:
        """Armazena a percepcao para uso no proximo `act`.

        Args:
            observation: lista de ids de setores com residuo.
                A percepcao eh validada contra o mundo real no
                momento do `act` (o ambiente pode ter mudado).
        """
        self._last_observation = list(observation)

    # ---------- Decisao ----------

    def act(self) -> Action:
        """Decide a proxima acao (COLLECT, MOVE ou WAIT).

        Mutacoes de estado sao feitas aqui:
        - COLLECT -> `mark_cleaned` no setor atual.
        - MOVE -> `move_to(target)` (incrementa step).
        - Em qualquer caso, consome energia proporcional.

        Returns:
            A `Action` escolhida para este passo.
        """
        current = self.state.current_sector
        sector = self._warehouse.get_sector(current)

        # Regra 1: se ha residuo aqui, coleta antes de planejar.
        if sector.has_waste:
            self._warehouse.collect_at(current, self.state.step)
            self.state.mark_cleaned(current)
            self.state.consume_energy(self._energy_per_collect)
            self.last_action = Action.COLLECT
            self.last_move_target = None
            return self.last_action

        # Regra 2: filtra goals pela regra anti-retorno.
        goals_in_world = self._warehouse.sectors_with_waste()
        allowed = [g for g in goals_in_world if self.state.can_return(g)]

        if not allowed:
            self.last_action = Action.WAIT
            self.last_move_target = None
            return self.last_action

        # Regra 3-4: planeja ate o goal mais proximo.
        problem = build_problem_from_warehouse(
            self._warehouse,
            initial_state=current,
            goals=allowed,
        )
        goal_node = self._planner(problem, heuristic=self._heuristic)
        if goal_node is None:
            self.last_action = Action.WAIT
            self.last_move_target = None
            return self.last_action

        path = goal_node.path()
        if len(path) < 2:
            # Ja esta sobre o goal mas sem residuo -> COLLECT nao
            # disparou (improvavel). Espera proxima percepcao.
            self.last_action = Action.WAIT
            self.last_move_target = None
            return self.last_action

        # Regra 5: caminha para o proximo no do caminho.
        next_sector = path[1].state
        self.state.move_to(next_sector)
        self.state.consume_energy(self._energy_per_step)
        self.last_action = Action.MOVE
        self.last_move_target = next_sector
        return self.last_action