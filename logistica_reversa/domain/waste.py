"""Residuo coletado pelo agente.

Waste eh um value object imutavel: uma vez criado, seus atributos
nao mudam. Isso facilita comparacoes e uso em conjuntos.
"""
from __future__ import annotations

from dataclasses import dataclass

from logistica_reversa.domain.enums import WasteType


@dataclass(frozen=True)
class Waste:
    """Um residuo presente em um setor.

    Attributes:
        waste_type: categoria do material.
        weight_kg: massa em quilogramas. Usado como proxy do "valor"
            coletado na funcao de performance do PEAS.
        step_created: passo da simulacao em que o residuo surgiu.
            Importante para modelar o carater dinamico do ambiente.
    """

    waste_type: WasteType
    weight_kg: float
    step_created: int

    def __post_init__(self) -> None:
        if self.weight_kg < 0:
            raise ValueError(f"weight_kg deve ser >= 0, recebido {self.weight_kg}")
        if self.step_created < 0:
            raise ValueError(
                f"step_created deve ser >= 0, recebido {self.step_created}"
            )
