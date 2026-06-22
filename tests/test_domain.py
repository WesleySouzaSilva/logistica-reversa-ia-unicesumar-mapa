"""Testes unitarios da camada de dominio.

Cobre:
- Enums: valores, quantidade, unicidade.
- Waste: imutabilidade, validacoes de construcao.
- Sector: estado inicial, coleta, deposito, validacoes.
- AgentState: cooldown, marcacao de limpeza, consumo de energia.
- SearchNode: reconstrucao de caminho, profundidade, custo.
"""
from __future__ import annotations

import pytest

from logistica_reversa.domain import (
    AgentState,
    AgentType,
    AlgorithmType,
    SearchNode,
    Sector,
    Waste,
    WasteType,
)


# ---------- Enums ----------

class TestEnums:
    def test_waste_types_present(self) -> None:
        values = {wt.value for wt in WasteType}
        assert "plastico" in values
        assert "metal" in values
        assert "papel" in values
        assert "vidro" in values
        assert "eletronico" in values

    def test_agent_types_count(self) -> None:
        # Quatro tipos canonicos de Russell & Norvig.
        assert len(AgentType) == 4

    def test_algorithm_types_count(self) -> None:
        # BFS, DFS, UCS, Greedy, A* = 5.
        assert len(AlgorithmType) == 5

    def test_enum_values_unique(self) -> None:
        for enum_cls in (WasteType, AgentType, AlgorithmType):
            values = [m.value for m in enum_cls]
            assert len(values) == len(set(values))


# ---------- Waste ----------

class TestWaste:
    def test_construction_ok(self) -> None:
        w = Waste(WasteType.PLASTICO, 1.5, step_created=0)
        assert w.waste_type is WasteType.PLASTICO
        assert w.weight_kg == 1.5
        assert w.step_created == 0

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError):
            Waste(WasteType.METAL, -0.1, step_created=0)

    def test_negative_step_raises(self) -> None:
        with pytest.raises(ValueError):
            Waste(WasteType.PAPEL, 1.0, step_created=-1)

    def test_immutable(self) -> None:
        w = Waste(WasteType.VIDRO, 2.0, step_created=3)
        with pytest.raises(Exception):  # FrozenInstanceError
            w.weight_kg = 5.0  # type: ignore[misc]

    def test_zero_weight_is_valid(self) -> None:
        # Zero eh valido: residuo sem massa util ainda eh um residuo.
        w = Waste(WasteType.ELETRONICO, 0.0, step_created=0)
        assert w.weight_kg == 0.0


# ---------- Sector ----------

class TestSector:
    def test_initial_state_empty(self) -> None:
        s = Sector(sector_id=0, x=0.0, y=0.0)
        assert s.has_waste is False
        assert s.waste is None
        assert s.cleaned_step is None

    def test_negative_id_raises(self) -> None:
        with pytest.raises(ValueError):
            Sector(sector_id=-1, x=0.0, y=0.0)

    def test_deposit_then_collect(self) -> None:
        s = Sector(sector_id=1, x=0.0, y=0.0)
        w = Waste(WasteType.METAL, 0.8, step_created=0)
        s.deposit(w)
        assert s.has_waste is True
        assert s.cleaned_step is None  # sujou de novo

        collected = s.collect(current_step=5)
        assert collected is w
        assert s.has_waste is False
        assert s.cleaned_step == 5

    def test_collect_when_empty_raises(self) -> None:
        s = Sector(sector_id=2, x=1.0, y=1.0)
        with pytest.raises(RuntimeError):
            s.collect(current_step=0)

    def test_double_deposit_raises(self) -> None:
        s = Sector(sector_id=3, x=2.0, y=2.0)
        s.deposit(Waste(WasteType.PAPEL, 1.0, step_created=0))
        with pytest.raises(RuntimeError):
            s.deposit(Waste(WasteType.VIDRO, 1.0, step_created=0))

    def test_deposit_resets_cleaned_step(self) -> None:
        s = Sector(sector_id=4, x=0.0, y=0.0)
        s.deposit(Waste(WasteType.PLASTICO, 0.5, step_created=0))
        s.collect(current_step=2)
        assert s.cleaned_step == 2
        s.deposit(Waste(WasteType.PLASTICO, 0.5, step_created=3))
        assert s.cleaned_step is None


# ---------- AgentState ----------

class TestAgentState:
    def test_initial_state(self) -> None:
        st = AgentState(current_sector=0)
        assert st.current_sector == 0
        assert st.step == 0
        assert st.cooldown == 3
        assert st.cleaned == {}

    def test_can_return_to_unvisited(self) -> None:
        st = AgentState(current_sector=0, cooldown=3)
        assert st.can_return(7) is True

    def test_cooldown_blocks_recent_return(self) -> None:
        st = AgentState(current_sector=0, step=5, cooldown=3)
        st.mark_cleaned(2)  # limpo no step 5
        # No mesmo step (step - cleaned = 0) nao pode retornar.
        assert st.can_return(2) is False

    def test_cooldown_allows_return_after_T_steps(self) -> None:
        st = AgentState(current_sector=0, step=5, cooldown=3)
        st.mark_cleaned(2)  # limpo no step 5
        # Avancar 3 passos: 8 - 5 = 3 >= cooldown(3).
        st.step = 8
        assert st.can_return(2) is True

    def test_move_advances_step(self) -> None:
        st = AgentState(current_sector=0)
        st.move_to(5)
        assert st.current_sector == 5
        assert st.step == 1

    def test_consume_energy(self) -> None:
        st = AgentState(current_sector=0, energy=10.0)
        st.consume_energy(3.0)
        assert st.energy == 7.0
        # Nao fica negativo: piso em zero.
        st.consume_energy(100.0)
        assert st.energy == 0.0

    def test_negative_energy_raises(self) -> None:
        st = AgentState(current_sector=0)
        with pytest.raises(ValueError):
            st.consume_energy(-1.0)


# ---------- SearchNode ----------

class TestSearchNode:
    def test_root_node(self) -> None:
        n = SearchNode(state="A")
        assert n.parent is None
        assert n.action is None
        assert n.path_cost == 0.0
        assert n.depth == 0

    def test_path_single_node(self) -> None:
        n = SearchNode(state="A")
        path = n.path()
        assert len(path) == 1
        assert path[0] is n

    def test_path_chain(self) -> None:
        # A -> B -> C
        c = SearchNode(state="C", action="to_C", path_cost=2.0, depth=2)
        b = SearchNode(state="B", action="to_B", path_cost=1.0, depth=1, parent=SearchNode(state="A"))
        c2 = SearchNode(state="C", action="to_C", path_cost=2.0, depth=2, parent=b)
        path = c2.path()
        assert [n.state for n in path] == ["A", "B", "C"]
        assert path[-1].path_cost == 2.0
