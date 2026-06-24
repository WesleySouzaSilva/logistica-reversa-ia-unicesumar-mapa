"""Testes da camada de servicos (Simulation).

Cobre:
- Validacoes do SimulationConfig.
- Determinismo do RNG (seed).
- Comportamento do loop: COLLECT, MOVE, WAIT.
- Condicoes de parada (energia, ambiente limpo, max_steps).
- Campos agregados de SimulationResult.
"""
from __future__ import annotations

import pytest

from logistica_reversa.agents.model_based import ModelBasedAgent
from logistica_reversa.agents.base import Action
from logistica_reversa.domain.enums import WasteType
from logistica_reversa.domain.sector import Sector
from logistica_reversa.domain.waste import Waste
from logistica_reversa.environment import Warehouse, generate_grid_warehouse
from logistica_reversa.services.simulation import (
    Simulation,
    SimulationConfig,
    SimulationResult,
    StepRecord,
)


# ---------- Helpers ----------


def make_wh_with_waste() -> Warehouse:
    """Cria um armazem 2x2 com 1 residuo conhecido no setor 0."""
    wh = generate_grid_warehouse(n_rows=2, n_cols=2)
    wh.get_sector(0).deposit(
        Waste(waste_type=WasteType.PAPEL, weight_kg=2.0, step_created=0)
    )
    return wh


# ---------- SimulationConfig ----------


class TestSimulationConfig:
    def test_defaults_are_valid(self) -> None:
        cfg = SimulationConfig()
        assert cfg.max_steps > 0
        assert 0.0 <= cfg.deposit_prob <= 1.0

    def test_invalid_max_steps(self) -> None:
        with pytest.raises(ValueError):
            SimulationConfig(max_steps=0)
        with pytest.raises(ValueError):
            SimulationConfig(max_steps=-1)

    def test_invalid_deposit_prob(self) -> None:
        with pytest.raises(ValueError):
            SimulationConfig(deposit_prob=-0.1)
        with pytest.raises(ValueError):
            SimulationConfig(deposit_prob=1.5)

    def test_invalid_initial_fraction(self) -> None:
        with pytest.raises(ValueError):
            SimulationConfig(initial_waste_fraction=-0.1)
        with pytest.raises(ValueError):
            SimulationConfig(initial_waste_fraction=1.5)


# ---------- StepRecord / SimulationResult ----------


class TestResultDataclasses:
    def test_steprecord_is_frozen(self) -> None:
        rec = StepRecord(
            step=0,
            sector=1,
            action=Action.MOVE,
            target=2,
            collected_kg=0.0,
            energy=100.0,
        )
        with pytest.raises(Exception):
            rec.step = 1  # type: ignore[misc]

    def test_efficiency_zero_when_no_energy(self) -> None:
        r = SimulationResult(
            total_collected_kg=5.0,
            energy_consumed=0.0,
        )
        assert r.efficiency == 0.0

    def test_efficiency_kg_per_energy(self) -> None:
        r = SimulationResult(
            total_collected_kg=10.0,
            energy_consumed=4.0,
        )
        assert r.efficiency == pytest.approx(2.5)


# ---------- Simulation.run ----------


class TestSimulationRun:
    def test_runs_and_returns_result(self) -> None:
        wh = make_wh_with_waste()
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        sim = Simulation(wh, agent, SimulationConfig(max_steps=10, deposit_prob=0.0))
        result = sim.run()
        assert isinstance(result, SimulationResult)
        assert len(result.history) > 0
        # Com deposit_prob=0.0 e so 1 residuo no inicio, a simulacao
        # termina quando o agente o coleta (total == 2.0) ou quando
        # ele chega ao estado limpo. Aceitamos qualquer nao-negativo.
        assert result.total_collected_kg >= 0.0
        assert result.total_collections + result.total_moves + result.total_waits > 0

    def test_initial_deposit_fraction(self) -> None:
        wh = generate_grid_warehouse(n_rows=4, n_cols=4)
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(
            max_steps=1,
            deposit_prob=0.0,
            initial_waste_fraction=0.5,
            seed=7,
        )
        Simulation(wh, agent, cfg).run()
        # 16 setores * 0.5 = 8 depositos iniciais; o agente coleta o
        # do seu setor inicial (0) no primeiro passo, restando 7.
        with_waste = len(wh.sectors_with_waste())
        assert with_waste == 7

    def test_deposit_prob_zero_means_no_dynamic_events(self) -> None:
        wh = make_wh_with_waste()
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(max_steps=30, deposit_prob=0.0)
        result = Simulation(wh, agent, cfg).run()
        # So existia 1 residuo no inicio; sem eventos dinamicos, apos
        # coleta-lo o ambiente fica limpo e a simulacao para.
        assert result.depleted_energy is False

    def test_stops_when_cleaned(self) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(
            max_steps=100,
            deposit_prob=0.0,
            initial_waste_fraction=0.2,
            seed=1,
        )
        result = Simulation(wh, agent, cfg).run()
        # Ambiente termina limpo (sem residuos) ao fim.
        assert len(wh.sectors_with_waste()) == 0

    def test_history_consistent_with_counters(self) -> None:
        wh = make_wh_with_waste()
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(max_steps=20, deposit_prob=0.0)
        result = Simulation(wh, agent, cfg).run()
        assert (
            result.total_collections
            + result.total_moves
            + result.total_waits
            == len(result.history)
        )

    def test_seed_is_deterministic(self) -> None:
        wh1 = make_wh_with_waste()
        wh2 = make_wh_with_waste()
        a1 = ModelBasedAgent(warehouse=wh1, initial_sector=0)
        a2 = ModelBasedAgent(warehouse=wh2, initial_sector=0)
        cfg = SimulationConfig(max_steps=20, deposit_prob=0.1, seed=123)
        r1 = Simulation(wh1, a1, cfg).run()
        r2 = Simulation(wh2, a2, cfg).run()
        assert r1.total_collected_kg == r2.total_collected_kg
        assert len(r1.history) == len(r2.history)

    def test_collect_step_records_kg(self) -> None:
        wh = make_wh_with_waste()
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(max_steps=5, deposit_prob=0.0)
        result = Simulation(wh, agent, cfg).run()
        collects = [r for r in result.history if r.action is Action.COLLECT]
        assert len(collects) >= 1
        assert sum(r.collected_kg for r in collects) == pytest.approx(
            result.total_collected_kg
        )

    def test_reached_max_steps_flag(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        # forca residuo em todos os setores e ambiente muito dinamico
        for sid in wh.positions().keys():
            wh.get_sector(sid).deposit(
                Waste(waste_type=WasteType.PAPEL, weight_kg=1.0, step_created=0)
            )
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(max_steps=3, deposit_prob=1.0, seed=0)
        result = Simulation(wh, agent, cfg).run()
        # Ou terminou por energia, ou por max_steps. Nao deve nunca
        # terminar "ambiente limpo" porque deposit_prob=1.0.
        assert result.depleted_energy or result.reached_max_steps

    def test_collect_increments_step_in_history(self) -> None:
        wh = make_wh_with_waste()
        agent = ModelBasedAgent(warehouse=wh, initial_sector=0)
        cfg = SimulationConfig(max_steps=5, deposit_prob=0.0)
        result = Simulation(wh, agent, cfg).run()
        # Cada step do history deve ter um step unico e sequencial.
        steps = [r.step for r in result.history]
        assert steps == list(range(len(steps)))
