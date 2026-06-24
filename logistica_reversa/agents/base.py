"""Contrato abstrato de agente.

Define a interface minima que todo agente deste projeto deve
implementar. O modelo segue Russell & Norvig, capitulo 2:
um agente eh uma funcao `perception -> action` mediada por
estado interno.

`Action` eh um enum simples que rotula o tipo de decisao tomada.
O destino concreto (em `MOVE`) eh exposto via atributo publico
no agente (`last_move_target`), evitando inflar o enum.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class Action(Enum):
    """Decisao discreta que um agente pode tomar em um passo.

    - MOVE: deslocar-se para um setor vizinho ou planejado.
    - COLLECT: coletar o residuo presente no setor atual.
    - WAIT: permanecer no lugar neste passo (nada a fazer).
    """

    MOVE = "move"
    COLLECT = "collect"
    WAIT = "wait"


class BaseAgent(ABC):
    """Contrato abstrato de agente.

    Subclasses devem implementar `perceive` (ingerir observacao)
    e `act` (decidir a proxima acao). O estado interno eh
    responsabilidade da subclasse; aqui nao ha campos.
    """

    @abstractmethod
    def perceive(self, observation: list[int]) -> None:
        """Atualiza o estado interno do agente com a percepcao atual.

        Args:
            observation: lista de ids de setores percebidos como
                relevantes (por convencao, setores com residuo).
        """

    @abstractmethod
    def act(self) -> Action:
        """Decide a proxima acao com base no estado interno.

        Returns:
            A `Action` escolhida para o passo atual.
        """