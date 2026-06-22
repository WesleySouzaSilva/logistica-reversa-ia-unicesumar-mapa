"""Setor do armazem (no do grafo).

Sector eh mutavel: o residuo pode aparecer, ser coletado, e o
setor pode ser marcado como limpo em um dado passo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from logistica_reversa.domain.waste import Waste


@dataclass
class Sector:
    """Um no do grafo do centro de distribuicao.

    Attributes:
        sector_id: identificador unico (inteiro >= 0).
        x: coordenada cartesiana X. Usada por heuristicas espaciais.
        y: coordenada cartesiana Y.
        waste: residuo atualmente no setor, ou None.
        cleaned_step: passo em que o setor foi limpo pela ultima vez,
            ou None se ainda nao foi limpo.
    """

    sector_id: int
    x: float
    y: float
    waste: Optional[Waste] = None
    cleaned_step: Optional[int] = field(default=None)

    def __post_init__(self) -> None:
        if self.sector_id < 0:
            raise ValueError(f"sector_id deve ser >= 0, recebido {self.sector_id}")

    @property
    def has_waste(self) -> bool:
        return self.waste is not None

    def collect(self, current_step: int) -> Waste:
        """Coleta o residuo atual, marcando o setor como limpo.

        Args:
            current_step: passo atual da simulacao.

        Returns:
            O residuo coletado.

        Raises:
            RuntimeError: se nao houver residuo no setor.
        """
        if self.waste is None:
            raise RuntimeError(f"setor {self.sector_id} nao tem residuo para coletar")
        collected = self.waste
        self.waste = None
        self.cleaned_step = current_step
        return collected

    def deposit(self, waste: Waste) -> None:
        """Deposita um novo residuo no setor.

        Args:
            waste: residuo a ser adicionado.

        Raises:
            RuntimeError: se ja houver residuo no setor.
        """
        if self.waste is not None:
            raise RuntimeError(
                f"setor {self.sector_id} ja tem residuo; colete antes de depositar"
            )
        self.waste = waste
        # Resetar marca de limpeza: novo residuo "sujou" o setor.
        self.cleaned_step = None
