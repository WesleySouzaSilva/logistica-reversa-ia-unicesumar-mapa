"""CLI argparse da aplicacao.

Subcomandos:
- `run`      : executa UMA simulacao e grava artefatos.
- `compare`  : executa N simulacoes (uma por planejador) e gera tabela.
- `snapshot` : salva a topologia de uma grade vazia em JSON.
- `report`   : agrega N `metrics.csv` previos em `relatorio-final.md`.

Cada subcomando produz:
- `metrics.md` e `metrics.csv` (tabela de uma linha).
- `warehouse.png` (plot do grafo + trajetoria).
- `run.json` (snapshot da configuracao, para reprodutibilidade).
- `comparison.md` (apenas em `compare`).
- `relatorio-final.md` (apenas em `report`).

A CLI NAO contem logica de decisao: ela apenas plameja argumentos,
constroi o ambiente/agente, e chama a `Simulation`.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Union

import pandas as pd

from logistica_reversa.agents.model_based import ModelBasedAgent
from logistica_reversa.environment import Warehouse, generate_grid_warehouse
from logistica_reversa.reports.metrics import (
    RunMetrics,
    build_metrics_table,
    format_table_md,
)
from logistica_reversa.search import (
    astar_search,
    bfs_search,
    dfs_search,
    greedy_search,
    ucs_search,
)
from logistica_reversa.services.simulation import (
    Simulation,
    SimulationConfig,
)
from logistica_reversa.visualization.plotter import plot_warehouse_graph


# Mapa nome -> funcao de busca. BFS/DFS/UCS nao aceitam `heuristic`
# (a interface uniforme do `BaseAgent.act` passa a heuristica para
# todos); envolvemos eles em um wrapper que ignora o argumento extra
# para manter o contrato consistente.
def _ignore_heuristic(fn: Callable) -> Callable:
    def wrapped(problem, heuristic=None):  # noqa: ARG001
        return fn(problem)
    wrapped.__name__ = f"wrapped_{fn.__name__}"
    return wrapped


PLANNER_REGISTRY: dict[str, Callable] = {
    "astar": astar_search,
    "greedy": greedy_search,
    "bfs": _ignore_heuristic(bfs_search),
    "ucs": _ignore_heuristic(ucs_search),
    "dfs": _ignore_heuristic(dfs_search),
}


# ---------- Helpers compartilhados ----------


def _build_warehouse(args: argparse.Namespace) -> Warehouse:
    """Constroi ou carrega o armazem conforme os argumentos."""
    if getattr(args, "warehouse", None):
        wh = Warehouse.load_json(args.warehouse)
        if args.start not in wh:
            raise ValueError(
                f"--start={args.start} nao existe no armazem carregado"
            )
        return wh
    return generate_grid_warehouse(n_rows=args.rows, n_cols=args.cols)


def _build_config(args: argparse.Namespace) -> SimulationConfig:
    """Constroi o `SimulationConfig` a partir dos argumentos."""
    return SimulationConfig(
        max_steps=args.max_steps,
        deposit_prob=args.deposit_prob,
        seed=args.seed,
        initial_waste_fraction=args.initial_fraction,
    )


def _build_agent(
    warehouse: Warehouse, args: argparse.Namespace, planner_name: str
) -> ModelBasedAgent:
    """Constroi o `ModelBasedAgent` com o planejador escolhido."""
    if planner_name not in PLANNER_REGISTRY:
        raise ValueError(
            f"planner desconhecido: {planner_name}. "
            f"Opcoes: {sorted(PLANNER_REGISTRY)}"
        )
    return ModelBasedAgent(
        warehouse=warehouse,
        initial_sector=args.start,
        planner=PLANNER_REGISTRY[planner_name],
    )


def _write_run_artifacts(
    output_dir: Path,
    args: argparse.Namespace,
    planner_name: str,
    result: Any,
) -> dict[str, Path]:
    """Persiste todos os artefatos de uma corrida. Retorna o dicionario."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tabela de metricas (md + csv).
    metrics = RunMetrics.from_result(
        result,
        label=f"{planner_name.upper()} + Model-Based",
        algorithm=planner_name,
    )
    df = build_metrics_table([metrics])
    md_path = output_dir / "metrics.md"
    md_path.write_text(format_table_md(df), encoding="utf-8")
    csv_path = output_dir / "metrics.csv"
    df.to_csv(csv_path, index=False)

    # 2. Plot do grafo + trajetoria.
    plot_path = plot_warehouse_graph(
        warehouse=_build_warehouse(args),  # recarregado limpo p/ plot
        history=result.history,
        output_path=output_dir / "warehouse.png",
        title=f"Trajetoria - {planner_name.upper()} (seed={args.seed})",
    )

    # 3. Snapshot da configuracao (reprodutibilidade).
    cfg_path = output_dir / "run.json"
    cfg_path.write_text(
        json.dumps(
            {
                "planner": planner_name,
                "rows": getattr(args, "rows", None),
                "cols": getattr(args, "cols", None),
                "start": args.start,
                "max_steps": args.max_steps,
                "deposit_prob": args.deposit_prob,
                "seed": args.seed,
                "initial_fraction": args.initial_fraction,
                "warehouse": getattr(args, "warehouse", None),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {"md": md_path, "csv": csv_path, "png": plot_path, "json": cfg_path}


# ---------- Subcomandos ----------


def _cmd_run(args: argparse.Namespace) -> int:
    wh = _build_warehouse(args)
    agent = _build_agent(wh, args, args.planner)
    result = Simulation(wh, agent, _build_config(args)).run()
    out_dir = Path(args.output_dir)
    paths = _write_run_artifacts(out_dir, args, args.planner, result)
    print(f"[run] artefatos salvos em {out_dir}/")
    for k, p in paths.items():
        print(f"  - {k}: {p}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    runs = []
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for planner_name in args.planners:
        wh = _build_warehouse(args)
        agent = _build_agent(wh, args, planner_name)
        result = Simulation(wh, agent, _build_config(args)).run()
        # Recarrega o armazem limpo so para o plot (o original ja tem
        # o estado do fim da corrida, o que polui a visualizacao).
        wh_clean = _build_warehouse(args)
        plot_path = out_dir / f"warehouse-{planner_name}.png"
        plot_warehouse_graph(
            warehouse=wh_clean,
            history=result.history,
            output_path=plot_path,
            title=f"Trajetoria - {planner_name.upper()} (seed={args.seed})",
        )
        runs.append(
            RunMetrics.from_result(
                result,
                label=f"{planner_name.upper()} + Model-Based",
                algorithm=planner_name,
            )
        )
    df = build_metrics_table(runs)
    md = out_dir / "comparison.md"
    md.write_text(format_table_md(df), encoding="utf-8")
    csv = out_dir / "comparison.csv"
    df.to_csv(csv, index=False)
    print(f"[compare] {len(runs)} corridas salvas em {out_dir}/")
    print(f"  - comparison.md\n  - comparison.csv")
    for p in sorted(out_dir.glob("warehouse-*.png")):
        print(f"  - {p.name}")
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    wh = generate_grid_warehouse(n_rows=args.rows, n_cols=args.cols)
    out = wh.save_json(args.out)
    print(f"[snapshot] armazem {args.rows}x{args.cols} salvo em {out}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Agrega N `metrics.csv` em `relatorio-final.md` + `relatorio-final.csv`."""
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for run_dir in args.run_dirs:
        csv_path = Path(run_dir) / "metrics.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"metrics.csv nao encontrado em {csv_path}"
            )
        frames.append(pd.read_csv(csv_path))

    df = pd.concat(frames, ignore_index=True)
    csv_out = out_dir / "relatorio-final.csv"
    df.to_csv(csv_out, index=False)

    header = (
        f"# Relatorio Final\n\n"
        f"- Diretorio de saida: `{out_dir}`\n"
        f"- Numero de corridas agregadas: {len(frames)}\n"
        f"- Gerado em: {datetime.now().isoformat(timespec='seconds')}\n\n"
    )
    md_out = out_dir / "relatorio-final.md"
    md_out.write_text(header + format_table_md(df), encoding="utf-8")

    print(f"[report] {len(frames)} corridas agregadas em {out_dir}/")
    print(f"  - {md_out.name}")
    print(f"  - {csv_out.name}")
    return 0


# ---------- Parser ----------


def build_parser() -> argparse.ArgumentParser:
    """Constroi o parser argparse com os subcomandos."""
    parser = argparse.ArgumentParser(
        prog="logistica-reversa",
        description=(
            "Logistica Reversa - simulacao de agente baseado em modelo "
            "para coleta de residuos em armazem (Unicesumar MAPA)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    p_run = sub.add_parser("run", help="executa uma simulacao completa")
    p_run.add_argument("--rows", type=int, default=5)
    p_run.add_argument("--cols", type=int, default=5)
    p_run.add_argument("--start", type=int, default=0)
    p_run.add_argument("--max-steps", type=int, default=200)
    p_run.add_argument("--deposit-prob", type=float, default=0.05)
    p_run.add_argument("--seed", type=int, default=42)
    p_run.add_argument("--initial-fraction", type=float, default=0.15)
    p_run.add_argument(
        "--planner",
        choices=sorted(PLANNER_REGISTRY),
        default="astar",
    )
    p_run.add_argument(
        "--warehouse",
        type=str,
        default=None,
        help="caminho de um JSON de topologia (substitui --rows/--cols)",
    )
    p_run.add_argument(
        "--output-dir", type=str, default="pipeline-outputs"
    )
    p_run.set_defaults(func=_cmd_run)

    # --- compare ---
    p_cmp = sub.add_parser(
        "compare", help="compara varios planejadores em paralelo"
    )
    p_cmp.add_argument("--rows", type=int, default=5)
    p_cmp.add_argument("--cols", type=int, default=5)
    p_cmp.add_argument("--start", type=int, default=0)
    p_cmp.add_argument("--max-steps", type=int, default=100)
    p_cmp.add_argument("--deposit-prob", type=float, default=0.05)
    p_cmp.add_argument("--seed", type=int, default=42)
    p_cmp.add_argument("--initial-fraction", type=float, default=0.15)
    p_cmp.add_argument(
        "--planners",
        nargs="+",
        choices=sorted(PLANNER_REGISTRY),
        default=["astar", "bfs"],
    )
    p_cmp.add_argument(
        "--warehouse",
        type=str,
        default=None,
        help="caminho de um JSON de topologia (substitui --rows/--cols)",
    )
    p_cmp.add_argument(
        "--output-dir", type=str, default="pipeline-outputs"
    )
    p_cmp.set_defaults(func=_cmd_compare)

    # --- snapshot ---
    p_snap = sub.add_parser(
        "snapshot", help="salva a topologia vazia de uma grade em JSON"
    )
    p_snap.add_argument("--rows", type=int, default=5)
    p_snap.add_argument("--cols", type=int, default=5)
    p_snap.add_argument(
        "--out", type=str, default="data/warehouse.json"
    )
    p_snap.set_defaults(func=_cmd_snapshot)

    # --- report ---
    p_report = sub.add_parser(
        "report",
        help="agrega varios metrics.csv em um relatorio final",
    )
    p_report.add_argument(
        "--run-dirs",
        nargs="+",
        required=True,
        help="um ou mais diretorios, cada um contendo um metrics.csv",
    )
    p_report.add_argument(
        "--output-dir",
        type=str,
        default="pipeline-outputs/final-report",
    )
    p_report.set_defaults(func=_cmd_report)

    return parser


def dispatch(args: Union[argparse.Namespace, list[str], None] = None) -> int:
    """Despacha o subcomando. Aceita None para usar `sys.argv`."""
    parser = build_parser()
    parsed = parser.parse_args(args)
    return parsed.func(parsed)
