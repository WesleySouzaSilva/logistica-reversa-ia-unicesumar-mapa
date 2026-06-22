"""Gerador deterministico de armazens em grade.

A funcao `generate_grid_warehouse` produz um `Warehouse` com
layout em grade `n_rows x n_cols`, conectado por adjacencia
4-vizinhos (cima, baixo, esquerda, direita). O id de cada setor
eh linearizado em ordem de linha: `id = r * n_cols + c`.

A coordenada (x, y) de cada setor eh sua posicao na grade, o que
torna as distancias Manhattan e Euclidiana entre vizinhos iguais
a 1.0, simplificando a calibracao das heuristicas.
"""
from __future__ import annotations

from logistica_reversa.domain.sector import Sector
from logistica_reversa.environment.warehouse import Warehouse


def generate_grid_warehouse(
    n_rows: int = 4,
    n_cols: int = 4,
    edge_weight: float = 1.0,
) -> Warehouse:
    """Gera um armazem em grade `n_rows x n_cols`.

    Args:
        n_rows: numero de linhas.
        n_cols: numero de colunas.
        edge_weight: custo de cada aresta (padrao 1.0).

    Returns:
        Um `Warehouse` com `n_rows * n_cols` setores e arestas
        4-vizinhas.

    Raises:
        ValueError: se `n_rows` ou `n_cols` forem < 1.
    """
    if n_rows < 1 or n_cols < 1:
        raise ValueError(
            f"n_rows e n_cols devem ser >= 1, recebido n_rows={n_rows} n_cols={n_cols}"
        )

    wh = Warehouse()
    # Adicionar nos
    for r in range(n_rows):
        for c in range(n_cols):
            sid = r * n_cols + c
            wh.add_sector(Sector(sector_id=sid, x=float(c), y=float(r)))

    # Adicionar arestas 4-vizinhas
    for r in range(n_rows):
        for c in range(n_cols):
            sid = r * n_cols + c
            if c + 1 < n_cols:  # direita
                wh.add_edge(sid, sid + 1, weight=edge_weight)
            if r + 1 < n_rows:  # abaixo
                wh.add_edge(sid, sid + n_cols, weight=edge_weight)

    return wh
