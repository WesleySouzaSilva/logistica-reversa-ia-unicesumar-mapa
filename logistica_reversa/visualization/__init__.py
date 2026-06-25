"""Camada de visualizacao.

Renderiza o grafo do armazem e a trajetoria do agente usando
`matplotlib` + `networkx`. O modulo principal eh
`logistica_reversa.visualization.plotter`.

Nenhuma logica de decisao vive aqui: o plotter apenas CONSOME
o `Warehouse` e o `history` retornado pela `Simulation`.
"""
from logistica_reversa.visualization.plotter import plot_warehouse_graph

__all__ = ["plot_warehouse_graph"]
