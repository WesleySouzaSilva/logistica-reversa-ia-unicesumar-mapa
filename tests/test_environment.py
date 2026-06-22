"""Testes unitarios da camada de ambiente.

Cobre:
- Gerador deterministico: cardinalidade, vizinhanca, conectividade.
- Warehouse: adicao de setores/arestas, vizinhos, distancias.
- Eventos dinamicos: deposito, coleta, deposito aleatorio via RNG.
- Erros e validacoes.
"""
from __future__ import annotations

import random

import pytest

from logistica_reversa.domain.enums import WasteType
from logistica_reversa.domain.sector import Sector
from logistica_reversa.domain.waste import Waste
from logistica_reversa.environment import Warehouse, generate_grid_warehouse


# ---------- Gerador ----------

class TestGridGenerator:
    def test_node_count(self) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=4)
        assert len(wh) == 12

    def test_invalid_dimensions_raise(self) -> None:
        with pytest.raises(ValueError):
            generate_grid_warehouse(n_rows=0, n_cols=3)
        with pytest.raises(ValueError):
            generate_grid_warehouse(n_rows=2, n_cols=0)

    def test_corner_neighbors(self) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        # No (0,0) tem apenas 2 vizinhos: direita (id=1) e abaixo (id=3)
        assert wh.neighbors(0) == [1, 3]

    def test_interior_neighbors(self) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        # No central (id=4) tem 4 vizinhos
        assert sorted(wh.neighbors(4)) == [1, 3, 5, 7]

    def test_grid_is_connected(self) -> None:
        wh = generate_grid_warehouse(n_rows=5, n_cols=5)
        import networkx as nx
        assert nx.is_connected(wh.graph)

    def test_positions_match_grid(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=3)
        pos = wh.positions()
        # id = 0 -> (0,0), id = 5 -> (2,1)
        assert pos[0] == (0.0, 0.0)
        assert pos[5] == (2.0, 1.0)


# ---------- Warehouse ----------

class TestWarehouse:
    def test_empty_warehouse_has_no_sectors(self) -> None:
        wh = Warehouse()
        assert len(wh) == 0

    def test_add_sector_and_retrieve(self) -> None:
        wh = Warehouse()
        wh.add_sector(Sector(sector_id=0, x=0.0, y=0.0))
        assert 0 in wh
        assert wh.get_sector(0).sector_id == 0

    def test_get_unknown_sector_raises(self) -> None:
        wh = Warehouse()
        with pytest.raises(KeyError):
            wh.get_sector(99)

    def test_add_edge_to_unknown_node_raises(self) -> None:
        wh = Warehouse()
        wh.add_sector(Sector(sector_id=0, x=0.0, y=0.0))
        with pytest.raises(KeyError):
            wh.add_edge(0, 99)

    def test_add_sector_updates_coordinates_preserving_object(self) -> None:
        wh = Warehouse()
        s = Sector(sector_id=0, x=0.0, y=0.0)
        s.deposit(Waste(WasteType.PAPEL, 1.0, step_created=0))
        wh.add_sector(s)
        # Re-adicionar o MESMO objeto atualiza coordenadas, mas preserva o estado
        s.x = 5.0
        s.y = 5.0
        wh.add_sector(s)
        assert wh.get_sector(0) is s
        assert wh.get_sector(0).has_waste is True
        assert wh.positions()[0] == (5.0, 5.0)

    def test_collect_at(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        wh.deposit_waste(0, Waste(WasteType.METAL, 0.5, step_created=0))
        collected = wh.collect_at(0, current_step=3)
        assert collected.weight_kg == 0.5
        assert wh.get_sector(0).has_waste is False
        assert wh.get_sector(0).cleaned_step == 3

    def test_sectors_with_waste(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        wh.deposit_waste(0, Waste(WasteType.PAPEL, 1.0, step_created=0))
        wh.deposit_waste(2, Waste(WasteType.VIDRO, 1.5, step_created=0))
        assert sorted(wh.sectors_with_waste()) == [0, 2]


# ---------- Deposito aleatorio ----------

class TestRandomDeposit:
    def test_deposit_chooses_empty_sector(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        rng = random.Random(42)
        target = wh.deposit_random_waste(
            Waste(WasteType.PLASTICO, 1.0, step_created=0), rng=rng
        )
        assert target is not None
        assert wh.get_sector(target).has_waste is True

    def test_determinism_same_seed(self) -> None:
        wh1 = generate_grid_warehouse(n_rows=2, n_cols=2)
        wh2 = generate_grid_warehouse(n_rows=2, n_cols=2)
        rng1 = random.Random(7)
        rng2 = random.Random(7)
        t1 = wh1.deposit_random_waste(
            Waste(WasteType.METAL, 1.0, step_created=0), rng=rng1
        )
        t2 = wh2.deposit_random_waste(
            Waste(WasteType.METAL, 1.0, step_created=0), rng=rng2
        )
        assert t1 == t2

    def test_no_empty_sector_returns_none(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        # Preencher todos
        for sid in range(4):
            wh.deposit_waste(sid, Waste(WasteType.PAPEL, 1.0, step_created=0))
        rng = random.Random(0)
        result = wh.deposit_random_waste(
            Waste(WasteType.PAPEL, 1.0, step_created=0), rng=rng
        )
        assert result is None


# ---------- Metricas espaciais ----------

class TestDistances:
    def test_manhattan_neighbor(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        # (0,0) -> (1,0) eh manhattan 1
        assert wh.manhattan(0, 1) == 1.0
        # (0,0) -> (0,1) eh manhattan 1
        assert wh.manhattan(0, 2) == 1.0
        # (0,0) -> (1,1) eh manhattan 2
        assert wh.manhattan(0, 3) == 2.0

    def test_euclidean_neighbor(self) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        assert wh.euclidean(0, 1) == pytest.approx(1.0)
        # Diagonal: sqrt(2)
        assert wh.euclidean(0, 3) == pytest.approx(2**0.5)

    def test_edge_weight(self) -> None:
        wh = Warehouse()
        wh.add_sector(Sector(sector_id=0, x=0.0, y=0.0))
        wh.add_sector(Sector(sector_id=1, x=1.0, y=0.0))
        wh.add_edge(0, 1, weight=2.5)
        assert wh.edge_weight(0, 1) == 2.5
