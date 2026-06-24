"""Camada de reports: metricas comparativas e formatacao de resultados.

Usa pandas para montar tabelas que comparam diferentes configuracoes
de busca/agente em uma mesma simulacao.
"""
from logistica_reversa.reports.metrics import (
    RunMetrics,
    build_metrics_table,
    format_table_md,
)

__all__ = [
    "RunMetrics",
    "build_metrics_table",
    "format_table_md",
]
