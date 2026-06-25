"""Testes de persistencia JSON do Warehouse (save/load)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from logistica_reversa.environment import generate_grid_warehouse
from logistica_reversa.environment.warehouse import Warehouse


class TestWarehouseIO:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        out = wh.save_json(tmp_path / "wh.json")
        assert out.exists()
        assert out.stat().st_size > 0

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        wh = generate_grid_warehouse(n_rows=2, n_cols=2)
        out = wh.save_json(tmp_path / "nested" / "deeper" / "wh.json")
        assert out.exists()

    def test_load_round_trip(self, tmp_path: Path) -> None:
        wh_orig = generate_grid_warehouse(n_rows=4, n_cols=4)
        out = wh_orig.save_json(tmp_path / "wh.json")
        wh_loaded = Warehouse.load_json(out)
        assert len(wh_loaded) == len(wh_orig)
        # Topologia equivalente: mesmas adjacencias.
        assert (
            sorted(wh_loaded.graph.edges())
            == sorted(wh_orig.graph.edges())
        )
        # Coordenadas preservadas.
        for sid in wh_orig.graph.nodes():
            assert wh_loaded.graph.nodes[sid]["x"] == wh_orig.graph.nodes[sid]["x"]
            assert wh_loaded.graph.nodes[sid]["y"] == wh_orig.graph.nodes[sid]["y"]

    def test_loaded_has_no_residue(self, tmp_path: Path) -> None:
        """Topologia apenas - residuos sao responsabilidade da simulacao."""
        from logistica_reversa.domain.enums import WasteType
        from logistica_reversa.domain.waste import Waste

        wh = generate_grid_warehouse(n_rows=3, n_cols=3)
        wh.get_sector(0).deposit(
            Waste(waste_type=WasteType.PAPEL, weight_kg=1.0, step_created=0)
        )
        out = wh.save_json(tmp_path / "wh.json")
        wh_loaded = Warehouse.load_json(out)
        assert len(wh_loaded.sectors_with_waste()) == 0

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Warehouse.load_json(tmp_path / "nao-existe.json")

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{ isto nao eh json valido }", encoding="utf-8")
        with pytest.raises(ValueError):
            Warehouse.load_json(bad)

    def test_load_missing_keys_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "no-edges.json"
        bad.write_text(json.dumps({"sectors": []}), encoding="utf-8")
        with pytest.raises(ValueError):
            Warehouse.load_json(bad)

    def test_load_edge_to_nonexistent_node_raises(
        self, tmp_path: Path
    ) -> None:
        bad = tmp_path / "ghost-edge.json"
        bad.write_text(
            json.dumps(
                {
                    "sectors": [{"id": 0, "x": 0, "y": 0}],
                    "edges": [{"a": 0, "b": 999, "weight": 1.0}],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            Warehouse.load_json(bad)

    def test_load_malformed_sector_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad-sector.json"
        bad.write_text(
            json.dumps(
                {
                    "sectors": [{"id": 0, "x": 0}],  # falta 'y'
                    "edges": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            Warehouse.load_json(bad)
