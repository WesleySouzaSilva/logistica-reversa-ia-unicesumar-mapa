"""Modelagem do centro de distribuicao como grafo.

`Warehouse` eh a fachada do ambiente. Encapsula:
- Um `networkx.Graph` que guarda adjacencia e coordenadas.
- Um dicionario `sector_id -> Sector` para acesso O(1) ao estado
  mutavel de cada no (residuo atual, marca de limpeza).

O ambiente eh **dinamico** e **estocastico** (ver Questao 1.2 do
MAPA): residuos podem ser depositados a qualquer momento via
`deposit_random_waste`, que usa um RNG injetado para garantir
reprodutibilidade.

Persistencia: `save_json` / `load_json` permitem serializar apenas
a topologia (sem residuos) para reproducao deterministica de cenarios.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Optional, Union

import networkx as nx

from logistica_reversa.domain.sector import Sector
from logistica_reversa.domain.waste import Waste


class Warehouse:
    """Grafo do centro de distribuicao + estado dos setores.

    Attributes:
        graph: `networkx.Graph` nao-direcionado. Nos sao identificados
            por `sector_id` (int) e contem atributos `x` e `y`. Arestas
            tem atributo `weight` (custo de movimentacao).
    """

    def __init__(self) -> None:
        self.graph: nx.Graph = nx.Graph()
        self._sectors: dict[int, Sector] = {}

    # ---------- Construcao ----------

    def add_sector(self, sector: Sector) -> None:
        """Adiciona um setor ao grafo (ou atualiza suas coordenadas).

        Idempotente: re-adicionar um setor existente apenas atualiza
        suas coordenadas no grafo, preservando o estado mutavel do
        `Sector` (residuo, cleaned_step).

        Args:
            sector: setor a ser adicionado.
        """
        self._sectors[sector.sector_id] = sector
        if self.graph.has_node(sector.sector_id):
            self.graph.nodes[sector.sector_id]["x"] = sector.x
            self.graph.nodes[sector.sector_id]["y"] = sector.y
        else:
            self.graph.add_node(
                sector.sector_id, x=sector.x, y=sector.y
            )

    def add_edge(self, a: int, b: int, weight: float = 1.0) -> None:
        """Conecta dois setores com peso (custo de mover entre eles).

        Args:
            a: id do primeiro setor.
            b: id do segundo setor.
            weight: custo de atravessar essa aresta.
        """
        if not self.graph.has_node(a):
            raise KeyError(f"setor {a} nao existe no armazem")
        if not self.graph.has_node(b):
            raise KeyError(f"setor {b} nao existe no armazem")
        self.graph.add_edge(a, b, weight=weight)

    # ---------- Consultas ----------

    def get_sector(self, sector_id: int) -> Sector:
        """Retorna o `Sector` correspondente ao id.

        Raises:
            KeyError: se o setor nao existir.
        """
        sector = self._sectors.get(sector_id)
        if sector is None:
            raise KeyError(f"setor {sector_id} nao existe no armazem")
        return sector

    def neighbors(self, sector_id: int) -> list[int]:
        """Lista os ids de setores vizinhos de `sector_id`."""
        return sorted(self.graph.neighbors(sector_id))

    def positions(self) -> dict[int, tuple[float, float]]:
        """Mapa id -> (x, y) de todos os setores."""
        return {
            nid: (data["x"], data["y"])
            for nid, data in self.graph.nodes(data=True)
        }

    # ---------- Deteccao de residuos ----------

    def sectors_with_waste(self) -> list[int]:
        """Ids dos setores que atualmente tem residuo."""
        return [sid for sid, s in self._sectors.items() if s.has_waste]

    # ---------- Eventos dinamicos ----------

    def deposit_waste(self, sector_id: int, waste: Waste) -> None:
        """Deposita um residuo no setor indicado.

        Args:
            sector_id: setor alvo.
            waste: residuo a depositar.

        Raises:
            KeyError: se o setor nao existir.
            RuntimeError: se o setor ja tiver residuo.
        """
        self.get_sector(sector_id).deposit(waste)

    def deposit_random_waste(
        self,
        waste: Waste,
        rng: random.Random,
        preferred_empty_only: bool = True,
    ) -> Optional[int]:
        """Deposita um residuo em um setor escolhido pelo RNG.

        Args:
            waste: residuo a depositar.
            rng: gerador aleatorio (injetado para reprodutibilidade).
            preferred_empty_only: se True, escolhe preferencialmente setores
                vazios; se nao houver nenhum, permite sobrescrever (mas o
                `Sector.deposit` bloqueia, entao neste caso a operacao
                falha silenciosamente retornando None).

        Returns:
            O id do setor onde o residuo foi depositado, ou None se nao
            foi possivel (todos ocupados e `preferred_empty_only=True`).
        """
        if preferred_empty_only:
            empty = [
                sid for sid, s in self._sectors.items() if not s.has_waste
            ]
            if not empty:
                return None
            target = rng.choice(empty)
        else:
            target = rng.choice(list(self._sectors.keys()))
        try:
            self.deposit_waste(target, waste)
        except RuntimeError:
            return None
        return target

    def collect_at(self, sector_id: int, current_step: int) -> Waste:
        """Coleta o residuo do setor (wrapper sobre `Sector.collect`).

        Args:
            sector_id: setor a limpar.
            current_step: passo atual da simulacao.

        Returns:
            O residuo coletado.
        """
        return self.get_sector(sector_id).collect(current_step)

    # ---------- Metricas espaciais ----------

    def edge_weight(self, a: int, b: int) -> float:
        """Custo de mover entre dois setores adjacentes."""
        return float(self.graph[a][b]["weight"])

    def manhattan(self, a: int, b: int) -> float:
        """Distancia de Manhattan entre dois setores (coordenadas no grafo)."""
        pa = self.graph.nodes[a]
        pb = self.graph.nodes[b]
        return abs(pa["x"] - pb["x"]) + abs(pa["y"] - pb["y"])

    def euclidean(self, a: int, b: int) -> float:
        """Distancia euclidiana entre dois setores."""
        pa = self.graph.nodes[a]
        pb = self.graph.nodes[b]
        return math.hypot(pa["x"] - pb["x"], pa["y"] - pb["y"])

    # ---------- Tamanho ----------

    def __len__(self) -> int:
        return self.graph.number_of_nodes()

    def __contains__(self, sector_id: int) -> bool:
        return self.graph.has_node(sector_id)

    # ---------- Persistencia (JSON) ----------

    def save_json(self, path: Union[str, Path]) -> Path:
        """Salva a topologia do armazem em JSON (sem residuos).

        Schema::

            {
              "sectors": [{"id": 0, "x": 0, "y": 0}, ...],
              "edges":   [{"a": 0, "b": 1, "weight": 1.0}, ...]
            }

        Args:
            path: caminho do arquivo de saida. Diretorios ausentes
                sao criados.

        Returns:
            O `Path` resolvido do arquivo escrito.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sectors": [
                {"id": nid, "x": data["x"], "y": data["y"]}
                for nid, data in self.graph.nodes(data=True)
            ],
            "edges": [
                {"a": a, "b": b, "weight": float(data.get("weight", 1.0))}
                for a, b, data in self.graph.edges(data=True)
            ],
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out.resolve()

    @classmethod
    def load_json(cls, path: Union[str, Path]) -> "Warehouse":
        """Carrega a topologia de um armazem a partir de JSON.

        Apenas nos e arestas sao reconstruidos. Os setores vem
        sem residuo (`Sector.waste = None`); o residuo sera
        depositado pela simulacao (eventos dinamicos).

        Args:
            path: caminho do arquivo JSON.

        Returns:
            Um novo `Warehouse` com a topologia carregada.

        Raises:
            FileNotFoundError: se o arquivo nao existir.
            ValueError: se o JSON estiver malformado, faltando chaves
                obrigatorias, ou referenciar setores inexistentes.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"arquivo de armazem nao encontrado: {p}")
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON invalido em {p}: {exc}") from exc

        if not isinstance(payload, dict) or "sectors" not in payload or "edges" not in payload:
            raise ValueError(
                f"JSON em {p} deve conter chaves 'sectors' e 'edges'"
            )

        wh = cls()
        for s in payload["sectors"]:
            if not all(k in s for k in ("id", "x", "y")):
                raise ValueError(f"setor malformado em {p}: {s}")
            wh.add_sector(
                Sector(sector_id=int(s["id"]), x=float(s["x"]), y=float(s["y"]))
            )
        for e in payload["edges"]:
            if not all(k in e for k in ("a", "b")):
                raise ValueError(f"aresta malformada em {p}: {e}")
            a, b = int(e["a"]), int(e["b"])
            if a not in wh or b not in wh:
                raise ValueError(
                    f"aresta referencia setor inexistente em {p}: {a}-{b}"
                )
            wh.add_edge(a, b, weight=float(e.get("weight", 1.0)))
        return wh
