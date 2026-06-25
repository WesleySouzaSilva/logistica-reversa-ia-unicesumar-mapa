"""Smoke tests do plotter (matplotlib + networkx)."""
from __future__ import annotations

from pathlib import Path

import pytest

from logistica_reversa.agents.base import Action
from logistica_reversa.environment import generate_grid_warehouse
from logistica_reversa.services.simulation import StepRecord
from logistica_reversa.visualization.plotter import _build_trajectory, plot_warehouse_graph


def _make_history(sequence: list[tuple[int, Action, int | None]]) -> list[StepRecord]:
    return [
        StepRecord(
            step=i,
            sector=s,
            action=a,
            target=t,
            collected_kg=0.0,
            energy=10.0,
        )
        for i, (s, a, t) in enumerate(sequence)
    ]


class TestBuildTrajectory:
    def test_empty_history(self) -> None:
        assert _build_trajectory([]) == []

    def test_dedups_consecutive_same_sector(self) -> None:
        history = _make_history(
            [
                (1, Action.MOVE, 1),  # MOVE 0->1, agente agora em 1
                (1, Action.COLLECT, None),  # COLLECT no mesmo setor
                (2, Action.MOVE, 2),  # MOVE 1->2, agente agora em 2
            ]
        )
        assert _build_trajectory(history) == [1, 2]

    def test_preserves_moves(self) -> None:
        history = _make_history(
            [
                (1, Action.MOVE, 1),  # 0->1
                (2, Action.MOVE, 2),  # 1->2
                (3, Action.MOVE, 3),  # 2->3
            ]
        )
        assert _build_trajectory(history) == [1, 2, 3]


class TestPlotWarehouseGraph:
    def test_creates_png(self, tmp_path: Path) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        history = _make_history(
            [
                (1, Action.MOVE, 1),  # 0->1
                (1, Action.COLLECT, None),
                (2, Action.MOVE, 2),  # 1->2
            ]
        )
        out = plot_warehouse_graph(
            wh, history, output_path=tmp_path / "plot.png"
        )
        assert out.exists()
        assert out.stat().st_size > 0
        # PNG magic bytes
        with out.open("rb") as f:
            assert f.read(8).startswith(b"\x89PNG\r\n\x1a\n")

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        history = _make_history([(0, Action.WAIT, None)])
        out = plot_warehouse_graph(
            wh, history, output_path=tmp_path / "deep" / "plot.png"
        )
        assert out.exists()

    def test_empty_history_still_renders(self, tmp_path: Path) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        out = plot_warehouse_graph(
            wh, [], output_path=tmp_path / "empty.png"
        )
        assert out.exists()
