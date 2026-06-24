"""Testes da camada de reports (metricas)."""
from __future__ import annotations

import pandas as pd
import pytest

from logistica_reversa.reports.metrics import (
    RunMetrics,
    build_metrics_table,
    format_table_md,
)
from logistica_reversa.services.simulation import SimulationResult


class TestRunMetrics:
    def test_from_result_populates_fields(self) -> None:
        r = SimulationResult(
            total_collected_kg=8.0,
            total_collections=4,
            total_moves=10,
            total_waits=1,
            energy_consumed=2.0,
        )
        # len(history) = 0, mas efficiency usa energy_consumed.
        m = RunMetrics.from_result(r, label="A*", algorithm="astar")
        assert m.label == "A*"
        assert m.algorithm == "astar"
        assert m.collected_kg == 8.0
        assert m.collections == 4
        assert m.moves == 10
        assert m.waits == 1
        assert m.steps == 0
        assert m.energy_consumed == 2.0
        assert m.efficiency == pytest.approx(4.0)


class TestBuildMetricsTable:
    def test_empty_iterable(self) -> None:
        df = build_metrics_table([])
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_columns_present(self) -> None:
        runs = [
            RunMetrics(
                label="A* + Model-Based",
                algorithm="astar",
                collected_kg=10.0,
                collections=5,
                moves=12,
                waits=2,
                steps=19,
                energy_consumed=4.0,
                efficiency=2.5,
            ),
            RunMetrics(
                label="BFS + Model-Based",
                algorithm="bfs",
                collected_kg=9.0,
                collections=5,
                moves=15,
                waits=1,
                steps=21,
                energy_consumed=4.5,
                efficiency=2.0,
            ),
        ]
        df = build_metrics_table(runs)
        assert len(df) == 2
        assert list(df.columns) == [
            "Config",
            "Algoritmo",
            "Coletado (kg)",
            "Coletas",
            "Movimentos",
            "Esperas",
            "Passos",
            "Energia",
            "Eficiencia (kg/u)",
        ]
        assert df.iloc[0]["Config"] == "A* + Model-Based"
        assert df.iloc[1]["Algoritmo"] == "bfs"


class TestFormatTableMd:
    def test_empty_returns_placeholder(self) -> None:
        df = build_metrics_table([])
        assert "Sem dados" in format_table_md(df)

    def test_non_empty_contains_rows(self) -> None:
        runs = [
            RunMetrics(
                label="A*",
                algorithm="astar",
                collected_kg=10.0,
                collections=5,
                moves=12,
                waits=2,
                steps=19,
                energy_consumed=4.0,
                efficiency=2.5,
            ),
        ]
        df = build_metrics_table(runs)
        md = format_table_md(df)
        assert "A*" in md
        assert "astar" in md
        assert "Coletado (kg)" in md
