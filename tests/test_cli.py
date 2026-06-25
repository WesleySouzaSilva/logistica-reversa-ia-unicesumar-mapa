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
        assert set(choices) == {"run", "compare", "snapshot", "report"}

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


class TestReport:
    """Cobertura do subcomando `report` (PR #8)."""

    def test_parser_defaults(self) -> None:
        p = build_parser()
        args = p.parse_args(["report", "--run-dirs", "a", "b"])
        assert args.run_dirs == ["a", "b"]
        assert args.output_dir == "pipeline-outputs/final-report"

    def test_parser_requires_run_dirs(self) -> None:
        p = build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["report"])

    def test_report_end_to_end(self, tmp_path: Path) -> None:
        # 1. Duas corridas previas em diretorios separados.
        out_a = tmp_path / "run-a"
        out_b = tmp_path / "run-b"
        for od, planner in [(out_a, "astar"), (out_b, "bfs")]:
            assert dispatch(
                [
                    "run",
                    "--rows", "3",
                    "--cols", "3",
                    "--max-steps", "10",
                    "--seed", "1",
                    "--planner", planner,
                    "--output-dir", str(od),
                ]
            ) == 0

        # 2. `report` agrega os metrics.csv.
        report_dir = tmp_path / "report"
        rc = dispatch(
            [
                "report",
                "--run-dirs", str(out_a), str(out_b),
                "--output-dir", str(report_dir),
            ]
        )
        assert rc == 0
        md = report_dir / "relatorio-final.md"
        csv = report_dir / "relatorio-final.csv"
        assert md.exists()
        assert csv.exists()
        # Conteudo minimo: tabela com 2 linhas (uma por run).
        content = md.read_text(encoding="utf-8")
        assert "# Relatorio Final" in content
        assert "Numero de corridas agregadas: 2" in content
        # CSV tem 2 linhas de dados + 1 header.
        lines = csv.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_report_missing_dir_raises(self, tmp_path: Path) -> None:
        # Diretorio inexistente -> FileNotFoundError (nao silencioso).
        with pytest.raises(FileNotFoundError):
            dispatch(
                [
                    "report",
                    "--run-dirs", str(tmp_path / "nao-existe"),
                    "--output-dir", str(tmp_path / "out"),
                ]
            )
