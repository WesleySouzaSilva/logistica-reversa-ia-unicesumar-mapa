"""Camada de ambiente.

Modela o centro de distribuicao como um grafo networkx cujos nos
sao instancias de `domain.Sector`. Tambem fornece o gerador
deterministico usado em testes e pela CLI.
"""
from logistica_reversa.environment.warehouse import Warehouse
from logistica_reversa.environment.warehouse_generator import (
    generate_grid_warehouse,
)

__all__ = ["Warehouse", "generate_grid_warehouse"]
