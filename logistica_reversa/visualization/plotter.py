"""Visualizacao do armazem e da trajetoria do agente.

A funcao `plot_warehouse_graph` desenha:

- O grafo (nos = setores, arestas = adjacencia).
- Setores com residuo atual (verde), vazios (cinza).
- O setor onde o agente parou (borda azul) - o ultimo do `history`.
- A trajetoria completa percorrida pelo agente (linha vermelha).
- Labels com o `sector_id` em cada no.

A figura eh salva em PNG e o `Figure` eh fechado ao final para nao
vazar memoria em execucoes em batch (CI, scripts).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union

import matplotlib

# Garante backend nao-interativo mesmo quando o modulo eh importado
# em ambientes sem DISPLAY (CI, containeres, Windows sem GUI).
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (depois do use("Agg"))
import networkx as nx  # noqa: E402

from logistica_reversa.environment.warehouse import Warehouse
from logistica_reversa.services.simulation import StepRecord


# Cores (constantes - facilitam troca sem magic numbers no meio da funcao)
_COLOR_WASTE = "#2ca02c"   # verde
_COLOR_EMPTY = "#bdbdbd"   # cinza
_COLOR_AGENT = "#1f77b4"   # azul
_COLOR_PATH = "#d62728"    # vermelho


def _build_trajectory(history: Iterable[StepRecord]) -> list[int]:
    """Extrai a lista de setores visitados em ordem a partir do history.

    Cada `StepRecord.sector` eh o setor onde o agente ESTA no fim do
    passo. Reconstruimos a trajetoria percorrendo pares (i, i+1):
    se os setores diferem, o agente moveu de `sector[i]` para
    `sector[i+1]`, e ambos sao mantidos. Consecutivos iguais (COLLECT
    ou WAIT no mesmo setor) sao deduplicados.
    """
    history_list = list(history)
    if not history_list:
        return []

    visited: list[int] = [history_list[0].sector]
    for i in range(1, len(history_list)):
        prev_sector = history_list[i - 1].sector
        cur_sector = history_list[i].sector
        if prev_sector != cur_sector:
            # Movimento: garante ambos os vertices na trajetoria.
            if visited[-1] != prev_sector:
                visited.append(prev_sector)
            if visited[-1] != cur_sector:
                visited.append(cur_sector)
        # COLLECT/WAIT no mesmo setor: deduplica (nada a fazer).
    return visited


def plot_warehouse_graph(
    warehouse: Warehouse,
    history: Iterable[StepRecord],
    output_path: Union[str, Path] = "pipeline-outputs/warehouse.png",
    title: str = "Armazem - trajetoria do agente",
) -> Path:
    """Plota o grafo do armazem com o estado e a trajetoria.

    Args:
        warehouse: ambiente (fornece o grafo e o estado dos setores).
        history: iteravel de `StepRecord` retornado pela simulacao.
        output_path: caminho do PNG de saida. Diretorios sao criados
            sob demanda. Default: `pipeline-outputs/warehouse.png`.
        title: titulo da figura.

    Returns:
        O `Path` resolvido do PNG salvo.
    """
    history_list = list(history)
    trajectory = _build_trajectory(history_list)
    final_sector = trajectory[-1] if trajectory else None

    positions = warehouse.positions()
    with_waste = set(warehouse.sectors_with_waste())

    # Cores dos nos: verde se tem residuo, cinza caso contrario.
    node_colors = [
        _COLOR_WASTE if nid in with_waste else _COLOR_EMPTY
        for nid in warehouse.graph.nodes()
    ]

    # Destaca o setor atual do agente com borda azul.
    edge_colors = [
        _COLOR_AGENT if nid == final_sector else "#000000"
        for nid in warehouse.graph.nodes()
    ]
    line_widths = [
        3.0 if nid == final_sector else 1.0
        for nid in warehouse.graph.nodes()
    ]

    fig, ax = plt.subplots(figsize=(8, 8))

    nx.draw_networkx_edges(
        warehouse.graph,
        pos=positions,
        ax=ax,
        edge_color="#7f7f7f",
        width=1.0,
    )
    nx.draw_networkx_nodes(
        warehouse.graph,
        pos=positions,
        ax=ax,
        node_color=node_colors,
        node_size=500,
        edgecolors=edge_colors,
        linewidths=line_widths,
    )
    nx.draw_networkx_labels(
        warehouse.graph,
        pos=positions,
        ax=ax,
        font_size=8,
        font_color="black",
    )

    # Sobrepoe a trajetoria (polyline) com os mesmos pontos do grafo.
    if len(trajectory) >= 2:
        path_coords = [positions[sid] for sid in trajectory]
        xs = [p[0] for p in path_coords]
        ys = [p[1] for p in path_coords]
        ax.plot(xs, ys, color=_COLOR_PATH, linewidth=2.0, alpha=0.7, zorder=1)
        # Pequenos circulos nos pontos da trajetoria.
        ax.scatter(xs, ys, color=_COLOR_PATH, s=30, zorder=3)

    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.margins(0.1)
    ax.axis("off")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)  # evita memory leak em execucoes em batch.

    return out.resolve()
