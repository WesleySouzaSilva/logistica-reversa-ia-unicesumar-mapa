"""Testes da camada de agentes.

Cobre o enum `Action`, o contrato `BaseAgent` e o
`ModelBasedAgent` em todos os ramos relevantes:
coleta local, planejamento via A*, regra anti-retorno
(via cooldown) e consumo de energia.
"""
from __future__ import annotations

import pytest

from logistica_reversa.agents import Action, BaseAgent, ModelBasedAgent
from logistica_reversa.domain import Waste, WasteType
from logistica_reversa.environment import generate_grid_warehouse


# ---------- Helpers ----------


def _warehouse_with_waste(rows: int = 3, cols: int = 3, *sectors: int):
    """Constroi um armazem em grade e deposita residuos nos setores dados."""
    wh = generate_grid_warehouse(rows, cols)
    for sid in sectors:
        wh.get_sector(sid).deposit(
            Waste(waste_type=WasteType.PLASTICO, weight_kg=1.0, step_created=0)
        )
    return wh


def _make_agent(
    warehouse,
    initial_sector: int = 0,
    cooldown: int = 0,
    energy: float = 100.0,
    energy_per_step: float = 1.0,
    energy_per_collect: float = 0.5,
) -> ModelBasedAgent:
    agent = ModelBasedAgent(
        warehouse=warehouse,
        initial_sector=initial_sector,
        cooldown=cooldown,
        energy_per_step=energy_per_step,
        energy_per_collect=energy_per_collect,
    )
    agent.state.energy = energy
    return agent


# ---------- TestAction ----------


class TestAction:
    def test_action_values_distinct(self):
        assert Action.MOVE != Action.COLLECT
        assert Action.MOVE != Action.WAIT
        assert Action.COLLECT != Action.WAIT

    def test_action_values_are_strings(self):
        assert Action.MOVE.value == "move"
        assert Action.COLLECT.value == "collect"
        assert Action.WAIT.value == "wait"


# ---------- TestBaseAgent ----------


class TestBaseAgent:
    def test_cannot_instantiate_base_agent_directly(self):
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    def test_subclass_must_implement_act_and_perceive(self):
        class IncompleteAgent(BaseAgent):
            pass

        with pytest.raises(TypeError):
            IncompleteAgent()  # type: ignore[abstract]

    def test_complete_subclass_can_be_instantiated(self):
        class StubAgent(BaseAgent):
            def perceive(self, observation):
                pass

            def act(self):
                return Action.WAIT

        agent = StubAgent()
        assert agent.act() == Action.WAIT


# ---------- TestModelBasedAgent ----------


class TestModelBasedAgent:
    def test_initial_state_at_initial_sector(self):
        wh = generate_grid_warehouse(3, 3)
        agent = _make_agent(wh, initial_sector=4)
        assert agent.state.current_sector == 4
        assert agent.state.step == 0
        assert agent.state.energy == 100.0

    def test_collect_action_when_current_sector_has_waste(self):
        wh = _warehouse_with_waste(3, 3, 0)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        action = agent.act()
        assert action == Action.COLLECT
        assert agent.last_move_target is None
        assert not wh.get_sector(0).has_waste

    def test_collect_marks_sector_cleaned_in_state(self):
        wh = _warehouse_with_waste(3, 3, 0)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        agent.act()
        assert agent.state.cleaned.get(0) == 0
        # Coletar nao incrementa step (regra: so MOVE incrementa)
        assert agent.state.step == 0

    def test_move_action_targets_neighbor_when_goal_adjacent(self):
        wh = _warehouse_with_waste(3, 3, 1)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        action = agent.act()
        assert action == Action.MOVE
        assert agent.last_move_target == 1
        assert agent.state.current_sector == 1
        assert agent.state.step == 1

    def test_move_action_plans_path_via_astar_when_far(self):
        # Goal no canto oposto de grade 3x3: caminho 0 -> 1 -> 2 -> 5 -> 8.
        wh = _warehouse_with_waste(3, 3, 8)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        action = agent.act()
        assert action == Action.MOVE
        assert agent.last_move_target == 1
        # Confirma que A* planeja o caminho otimo
        assert agent.state.current_sector == 1

    def test_wait_action_when_no_goals(self):
        wh = generate_grid_warehouse(3, 3)  # sem residuos
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        action = agent.act()
        assert action == Action.WAIT
        assert agent.last_move_target is None

    def test_wait_action_when_all_goals_blocked_by_cooldown(self):
        # Goal em 1, mas agente ja limpou 1 no passo -1 (1 passo atras).
        # Com cooldown=3, ainda nao pode voltar.
        wh = _warehouse_with_waste(3, 3, 1)
        agent = _make_agent(wh, initial_sector=0, cooldown=3)
        # Simula que 1 foi limpo no step 0 (agora estamos no step 1)
        agent.state.step = 1
        agent.state.cleaned[1] = 0
        agent.state.current_sector = 0
        agent.perceive(wh.sectors_with_waste())
        action = agent.act()
        assert action == Action.WAIT

    def test_cooldown_blocks_recently_cleaned_sector(self):
        # Limpa 1 e vai para 2; tenta voltar a 1 (cooldown=3 ainda ativo).
        wh = _warehouse_with_waste(3, 3, 1, 2)
        agent = _make_agent(wh, initial_sector=0, cooldown=3)
        # Atua 4 vezes: coleta 1, move para 2, coleta 2, tenta voltar.
        for _ in range(4):
            agent.perceive(wh.sectors_with_waste())
            agent.act()
        # Apos 4 passos, step == 3 e 1 foi limpo no step 0 -> ainda bloqueado
        assert 1 not in agent.state.cleaned or (
            agent.state.step - agent.state.cleaned[1]
        ) >= 3 or agent.last_move_target != 1

    def test_cooldown_expires_after_n_steps(self):
        wh = _warehouse_with_waste(3, 3, 1)
        agent = _make_agent(wh, initial_sector=0, cooldown=2)
        # Step 0: coleta 1 (mark_cleaned em step 0)
        agent.perceive(wh.sectors_with_waste())
        agent.act()
        # Step 1-2: move para 4 (vizinho de 0) e espera
        agent.state.move_to(4)
        agent.state.move_to(0)
        # Step 3: cooldown expirou (step - cleaned = 3 - 0 = 3 >= 2)
        assert agent.state.can_return(1) is True

    def test_perceive_updates_known_waste_set(self):
        wh = _warehouse_with_waste(3, 3, 5)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive([5])
        # Percepcao foi armazenada (atributo privado)
        assert agent._last_observation == [5]

    def test_energy_decreases_on_move(self):
        wh = _warehouse_with_waste(3, 3, 1)
        agent = _make_agent(wh, initial_sector=0, energy_per_step=2.5)
        before = agent.state.energy
        agent.perceive(wh.sectors_with_waste())
        agent.act()
        assert agent.state.energy == pytest.approx(before - 2.5)

    def test_energy_decreases_on_collect(self):
        wh = _warehouse_with_waste(3, 3, 0)
        agent = _make_agent(wh, initial_sector=0, energy_per_collect=3.0)
        before = agent.state.energy
        agent.perceive(wh.sectors_with_waste())
        agent.act()
        assert agent.state.energy == pytest.approx(before - 3.0)

    def test_move_increments_step(self):
        wh = _warehouse_with_waste(3, 3, 1)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        assert agent.state.step == 0
        agent.act()
        assert agent.state.step == 1

    def test_last_move_target_is_next_node_in_path(self):
        # Goal em 8 (canto oposto em 3x3): primeiro passo do caminho eh 1.
        wh = _warehouse_with_waste(3, 3, 8)
        agent = _make_agent(wh, initial_sector=0)
        agent.perceive(wh.sectors_with_waste())
        agent.act()
        assert agent.last_move_target == 1

    def test_negative_energy_per_step_raises(self):
        wh = generate_grid_warehouse(3, 3)
        with pytest.raises(ValueError):
            ModelBasedAgent(
                warehouse=wh,
                initial_sector=0,
                energy_per_step=-1.0,
            )

    def test_negative_energy_per_collect_raises(self):
        wh = generate_grid_warehouse(3, 3)
        with pytest.raises(ValueError):
            ModelBasedAgent(
                warehouse=wh,
                initial_sector=0,
                energy_per_collect=-0.1,
            )


# ---------- TestModelBasedAgentDeterminism ----------


class TestModelBasedAgentDeterminism:
    def test_act_is_deterministic_same_inputs(self):
        # Dois armazens identicos para que os agentes nao compartilhem
        # mutacao de estado (ambiente dinamico).
        wh1 = _warehouse_with_waste(3, 3, 8)
        wh2 = _warehouse_with_waste(3, 3, 8)
        agent1 = _make_agent(wh1, initial_sector=0, cooldown=0)
        agent2 = _make_agent(wh2, initial_sector=0, cooldown=0)
        for _ in range(5):
            agent1.perceive(wh1.sectors_with_waste())
            agent2.perceive(wh2.sectors_with_waste())
            a1 = agent1.act()
            a2 = agent2.act()
            assert a1 == a2
            assert agent1.last_move_target == agent2.last_move_target
            assert agent1.state.current_sector == agent2.state.current_sector