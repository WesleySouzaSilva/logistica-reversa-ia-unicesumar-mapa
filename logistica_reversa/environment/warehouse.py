"""Modelagem do centro de distribuicao como grafo.

`Warehouse` eh a fachada do ambiente. Encapsula:
- Um `networkx.Graph` que guarda adjacencia e coordenadas.
- Um dicionario `sector_id -> Sector` para acesso O(1) ao estado
  mutavel de cada no (residuo atual, marca de limpeza).

O ambiente eh **dinamico** e **estocastico** (ver Questao 1.2 do
MAPA): residuos podem ser depositados a qualquer momento via
`deposit_random_waste`, que usa um RNG injetado para garantir
reprodutibilidade.
"""
from __future__ import annotations

import math
import random
from typing import Optional

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
