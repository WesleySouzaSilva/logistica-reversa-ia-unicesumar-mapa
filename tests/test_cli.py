"""Testes do parser CLI (argparse + dispatch)."""
from __future__ import annotations

from pathlib import Path

import pytest

from logistica_reversa.cli.parser import PLANNER_REGISTRY, build_parser, dispatch


class TestBuildParser:
    def test_returns_parser(self) -> None:
        p = build_parser()
        assert p is not None
        # Subcomandos registrados.
        choices = p._subparsers._group_actions[0].choices
        assert set(choices) == {"run", "compare", "snapshot"}

    def test_run_defaults(self) -> None:
        p = build_parser()
        args = p.parse_args(["run"])
        assert args.rows == 5
        assert args.cols == 5
        assert args.planner == "astar"
        assert args.seed == 42

    def test_run_with_explicit_args(self) -> None:
        p = build_parser()
        args = p.parse_args(
            [
                "run",
                "--rows", "4",
                "--cols", "6",
                "--start", "3",
                "--planner", "bfs",
                "--seed", "7",
            ]
        )
        assert args.rows == 4
        assert args.cols == 6
        assert args.start == 3
        assert args.planner == "bfs"
        assert args.seed == 7

    def test_compare_collects_planners(self) -> None:
        p = build_parser()
        args = p.parse_args(
            ["compare", "--planners", "astar", "bfs", "ucs"]
        )
        assert args.planners == ["astar", "bfs", "ucs"]

    def test_snapshot_defaults(self) -> None:
        p = build_parser()
        args = p.parse_args(["snapshot"])
        assert args.rows == 5
        assert args.cols == 5
        assert args.out == "data/warehouse.json"


class TestDispatch:
    def test_snapshot_end_to_end(self, tmp_path: Path) -> None:
        out = tmp_path / "wh.json"
        rc = dispatch(["snapshot", "--rows", "3", "--cols", "3", "--out", str(out)])
        assert rc == 0
        assert out.exists()
        assert out.stat().st_size > 0

    def test_run_end_to_end(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        rc = dispatch(
            [
                "run",
                "--rows", "3",
                "--cols", "3",
                "--max-steps", "20",
                "--seed", "1",
                "--planner", "astar",
                "--output-dir", str(out_dir),
            ]
        )
        assert rc == 0
        assert (out_dir / "metrics.md").exists()
        assert (out_dir / "metrics.csv").exists()
        assert (out_dir / "warehouse.png").exists()
        assert (out_dir / "run.json").exists()

    def test_compare_end_to_end(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "cmp"
        rc = dispatch(
            [
                "compare",
                "--rows", "3",
                "--cols", "3",
                "--max-steps", "10",
                "--seed", "1",
                "--planners", "astar", "bfs",
                "--output-dir", str(out_dir),
            ]
        )
        assert rc == 0
        assert (out_dir / "comparison.md").exists()
        assert (out_dir / "comparison.csv").exists()
        assert (out_dir / "warehouse-astar.png").exists()
        assert (out_dir / "warehouse-bfs.png").exists()

    def test_run_with_warehouse_json(self, tmp_path: Path) -> None:
        wh_path = tmp_path / "wh.json"
        # Primeiro gera o snapshot.
        dispatch(["snapshot", "--rows", "3", "--cols", "3", "--out", str(wh_path)])
        # Depois carrega dele.
        out_dir = tmp_path / "out"
        rc = dispatch(
            [
                "run",
                "--warehouse", str(wh_path),
                "--start", "0",
                "--max-steps", "10",
                "--seed", "1",
                "--planner", "bfs",
                "--output-dir", str(out_dir),
            ]
        )
        assert rc == 0
        assert (out_dir / "run.json").exists()


class TestPlannerRegistry:
    def test_contains_all_algorithms(self) -> None:
        for name in ("astar", "greedy", "bfs", "ucs", "dfs"):
            assert name in PLANNER_REGISTRY
