"""Estado interno do agente baseado em modelo.

Este modelo sustenta o agente da Questao 1.3 do MAPA: ele
lembra quais setores ja visitou/limpou e respeita um tempo
minimo de cooldown T antes de retornar a um setor que acabou
de limpar (regra anti-retorno para preservar autonomia
energetica).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentState:
    """Estado interno do agente baseado em modelo.

    Attributes:
        current_sector: id do setor onde o agente esta agora.
        cleaned: mapa setor_id -> passo em que foi limpo pela ultima
            vez. Usado para aplicar a regra anti-retorno.
        step: passo atual da simulacao.
        cooldown: T, numero minimo de passos antes de poder retornar
            a um setor recem-limpo.
        energy: energia restante (proxy da autonomia). Opcional;
            preenchido pela simulacao.
    """

    current_sector: int
    cleaned: dict[int, int] = field(default_factory=dict)
    step: int = 0
    cooldown: int = 3
    energy: float = 100.0

    def can_return(self, sector_id: int) -> bool:
        """Verifica se o agente pode retornar a um setor respeitando o cooldown.

        Args:
            sector_id: candidato a proximo setor.

        Returns:
            True se o setor nunca foi limpo OU se ja passou cooldown
            passos desde a ultima limpeza. False caso contrario.
        """
        last_cleaned = self.cleaned.get(sector_id)
        if last_cleaned is None:
            return True
        return (self.step - last_cleaned) >= self.cooldown

    def mark_cleaned(self, sector_id: int) -> None:
        """Registra que o setor foi limpo neste passo.

        Args:
            sector_id: setor que acabou de ser limpo.
        """
        self.cleaned[sector_id] = self.step

    def move_to(self, sector_id: int) -> None:
        """Atualiza o setor atual e avanca o passo.

        Args:
            sector_id: novo setor onde o agente esta.
        """
        self.current_sector = sector_id
        self.step += 1

    def consume_energy(self, amount: float) -> None:
        """Reduz a energia disponivel.

        Args:
            amount: energia a subtrair (deve ser >= 0).
        """
        if amount < 0:
            raise ValueError(f"consumo de energia deve ser >= 0, recebido {amount}")
        self.energy = max(0.0, self.energy - amount)
