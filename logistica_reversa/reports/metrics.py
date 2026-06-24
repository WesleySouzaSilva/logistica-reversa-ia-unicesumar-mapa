"""Metricas comparativas entre simulacoes.

Esta camada eh deliberadamente fina: recebe uma lista de
`SimulationResult` (juntamente com o rotulo do algoritmo/agente
usado em cada uma) e produz:

- `RunMetrics`: resumo de uma corrida (uma linha da tabela).
- `build_metrics_table`: monta um `pandas.DataFrame` com todas as
  linhas, pronto para visualizacao ou exportacao.
- `format_table_md`: formata o DataFrame em uma tabela Markdown
  (util para o relatorio final).

A camada NAO executa simulacoes nem conhece o agente concreto: ela
consome apenas `SimulationResult`. Isso permite comparar livremente
qualquer combinacao de agente/planejador/seed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd

from logistica_reversa.services.simulation import SimulationResult


@dataclass(frozen=True)
class RunMetrics:
    """Resumo de uma simulacao (uma linha da tabela comparativa).

    Attributes:
        label: rotulo da corrida (ex.: 'A* + Model-Based').
        algorithm: nome do algoritmo de busca (ex.: 'astar', 'bfs').
        collected_kg: total de kg coletados.
        collections: numero de acoes COLLECT.
        moves: numero de acoes MOVE.
        waits: numero de acoes WAIT.
        steps: numero de passos efetivamente executados.
        energy_consumed: energia total consumida.
        efficiency: kg por unidade de energia (PEAS).
    """

    label: str
    algorithm: str
    collected_kg: float
    collections: int
    moves: int
    waits: int
    steps: int
    energy_consumed: float
    efficiency: float

    @classmethod
    def from_result(
        cls, result: SimulationResult, label: str, algorithm: str
    ) -> "RunMetrics":
        return cls(
            label=label,
            algorithm=algorithm,
            collected_kg=result.total_collected_kg,
            collections=result.total_collections,
            moves=result.total_moves,
            waits=result.total_waits,
            steps=len(result.history),
            energy_consumed=result.energy_consumed,
            efficiency=round(result.efficiency, 4),
        )


def build_metrics_table(runs: Iterable[RunMetrics]) -> pd.DataFrame:
    """Constroi um DataFrame pandas com as metricas de cada corrida.

    Args:
        runs: iteravel de RunMetrics (tipicamente um por combinacao
            agente/planejador).

    Returns:
        DataFrame com colunas: label, algorithm, collected_kg,
        collections, moves, waits, steps, energy_consumed, efficiency.
    """
    rows = [
        {
            "Config": r.label,
            "Algoritmo": r.algorithm,
            "Coletado (kg)": r.collected_kg,
            "Coletas": r.collections,
            "Movimentos": r.moves,
            "Esperas": r.waits,
            "Passos": r.steps,
            "Energia": r.energy_consumed,
            "Eficiencia (kg/u)": r.efficiency,
        }
        for r in runs
    ]
    return pd.DataFrame(rows)


def format_table_md(df: pd.DataFrame, float_fmt: str = "{:.3f}") -> str:
    """Formata um DataFrame em tabela Markdown.

    Args:
        df: DataFrame de metricas (tipicamente de `build_metrics_table`).
        float_fmt: format string para colunas de ponto flutuante.

    Returns:
        String com a tabela em Markdown.
    """
    if df.empty:
        return "_Sem dados._"
    return df.to_markdown(index=False, floatfmt=float_fmt)
