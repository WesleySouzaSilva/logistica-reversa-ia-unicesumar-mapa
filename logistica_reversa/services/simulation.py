"""Loop de simulacao agente x ambiente.

A simulacao implementa o ciclo classico de Russell & Norvig:

    for t in 0..max_steps:
        env.step_events(t)        # ambiente muda (dinamico)
        action = agent.perceive_and_act(...)
        env.apply(action)

Aqui separamos `perceive` e `act` no agente via `perceive(percepts)`
seguido de `act() -> Action`, exatamente como definido em
`agents/base.py`.

Politicas suportadas:
- Parar quando o agente ficar sem energia.
- Parar quando nao houver mais residuos visiveis no armazem
  (apos um minimo de passos para nao abortar simulacoes muito
  pequenas).
- Parar quando `max_steps` for atingido (seguranca).

O resultado agrega um historico de passos (StepRecord) e contadores
agregados (coletas, kg, energia consumida) que alimentam
`reports/metrics.py`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from logistica_reversa.agents.base import Action, BaseAgent
from logistica_reversa.domain.enums import WasteType
from logistica_reversa.domain.waste import Waste
from logistica_reversa.environment.warehouse import Warehouse


@dataclass(frozen=True)
class SimulationConfig:
    """Configuracao de uma simulacao.

    Attributes:
        max_steps: numero maximo de passos antes de parar (seguranca).
        deposit_prob: probabilidade por passo de surgir um residuo
            aleatorio em algum setor vazio (modela ambiente dinamico).
        seed: semente do RNG (torna a simulacao reprodutivel).
        initial_waste_fraction: fracao inicial de setores com residuo
            no inicio da simulacao.
    """

    max_steps: int = 200
    deposit_prob: float = 0.05
    seed: int = 42
    initial_waste_fraction: float = 0.15

    def __post_init__(self) -> None:
        if self.max_steps <= 0:
            raise ValueError(f"max_steps deve ser > 0, recebido {self.max_steps}")
        if not 0.0 <= self.deposit_prob <= 1.0:
            raise ValueError(
                f"deposit_prob deve estar em [0, 1], recebido {self.deposit_prob}"
            )
        if not 0.0 <= self.initial_waste_fraction <= 1.0:
            raise ValueError(
                "initial_waste_fraction deve estar em [0, 1], "
                f"recebido {self.initial_waste_fraction}"
            )


@dataclass(frozen=True)
class StepRecord:
    """Registro imutavel de um passo da simulacao.

    Attributes:
        step: indice do passo (0-based).
        sector: setor onde o agente estava no inicio do passo.
        action: acao tomada (MOVE/COLLECT/WAIT).
        target: destino do MOVE, ou None.
        collected_kg: kg coletados neste passo (0 se nao COLLECT).
        energy: energia restante ao fim do passo.
    """

    step: int
    sector: int
    action: Action
    target: Optional[int]
    collected_kg: float
    energy: float


@dataclass(frozen=True)
class SimulationResult:
    """Resultado agregado de uma simulacao.

    Attributes:
        history: lista de registros de cada passo.
        total_collected_kg: soma de kg coletados.
        total_collections: numero de acoes COLLECT.
        total_moves: numero de acoes MOVE.
        total_waits: numero de acoes WAIT.
        energy_consumed: energia total consumida (inicial - final).
        final_energy: energia ao fim da simulacao.
        reached_max_steps: True se parou por atingir max_steps.
        depleted_energy: True se parou por falta de energia.
    """

    history: list[StepRecord] = field(default_factory=list)
    total_collected_kg: float = 0.0
    total_collections: int = 0
    total_moves: int = 0
    total_waits: int = 0
    energy_consumed: float = 0.0
    final_energy: float = 0.0
    reached_max_steps: bool = False
    depleted_energy: bool = False

    @property
    def efficiency(self) -> float:
        """Eficiencia PEAS: kg coletados por unidade de energia."""
        if self.energy_consumed <= 0.0:
            return 0.0
        return self.total_collected_kg / self.energy_consumed


class Simulation:
    """Loop principal: orquestra agente, ambiente e o relogio.

    Attributes:
        warehouse: ambiente (grafo + setores).
        agent: agente (qualquer subclasse de BaseAgent).
        config: configuracao (max_steps, RNG, etc).
    """

    def __init__(
        self,
        warehouse: Warehouse,
        agent: BaseAgent,
        config: Optional[SimulationConfig] = None,
    ) -> None:
        self.warehouse = warehouse
        self.agent = agent
        self.config = config or SimulationConfig()
        self._rng = random.Random(self.config.seed)

    # ---------------- helpers ----------------

    def _pick_waste(self, step: int) -> Waste:
        return Waste(
            waste_type=self._rng.choice(list(WasteType)),
            weight_kg=round(self._rng.uniform(0.5, 5.0), 2),
            step_created=step,
        )

    def _initial_deposit(self) -> None:
        """Deposita residuos em uma fracao inicial dos setores vazios."""
        all_ids = list(self.warehouse.positions().keys())
        empty_sectors = [
            sid for sid in all_ids if not self.warehouse.get_sector(sid).has_waste
        ]
        if not empty_sectors:
            return
        n = int(len(empty_sectors) * self.config.initial_waste_fraction)
        if n == 0 and self.config.initial_waste_fraction > 0:
            n = 1
        chosen = self._rng.sample(empty_sectors, k=min(n, len(empty_sectors)))
        for sid in chosen:
            self.warehouse.get_sector(sid).deposit(self._pick_waste(0))

    def _maybe_dynamic_event(self, step: int) -> None:
        """Sorteia se um novo residuo aparece neste passo (ambiente dinamico)."""
        if self._rng.random() >= self.config.deposit_prob:
            return
        all_ids = list(self.warehouse.positions().keys())
        empty = [sid for sid in all_ids if not self.warehouse.get_sector(sid).has_waste]
        if not empty:
            return
        sid = self._rng.choice(empty)
        self.warehouse.get_sector(sid).deposit(self._pick_waste(step))

    def _has_any_waste(self) -> bool:
        return len(self.warehouse.sectors_with_waste()) > 0

    # ---------------- public API ----------------

    def run(self) -> SimulationResult:
        """Executa a simulacao ate uma condicao de parada.

        Returns:
            SimulationResult com historico e contadores.
        """
        cfg = self.config
        self._initial_deposit()

        history: list[StepRecord] = []
        total_collections = 0
        total_moves = 0
        total_waits = 0
        total_kg = 0.0
        depleted_energy = False

        initial_energy = self.agent.state.energy
        last_step_index = -1

        for step in range(cfg.max_steps):
            # 1. Ambiente pode mudar antes do agente decidir.
            self._maybe_dynamic_event(step)

            # 2. Snapshot do setor atual (para contabilizar COLLECT).
            sector_before = self.warehouse.get_sector(
                self.agent.state.current_sector
            )
            kg_before = (
                sector_before.waste.weight_kg if sector_before.has_waste else 0.0
            )

            # 3. Agente percebe e decide. O ModelBasedAgent ja cuida
            #    de coletar/mover internamente; o servico apenas
            #    contabiliza o efeito.
            self.agent.perceive(self.warehouse.sectors_with_waste())
            action = self.agent.act()
            target = self.agent.last_move_target

            collected_kg = 0.0
            if action is Action.COLLECT:
                collected_kg = kg_before
                total_collections += 1
                total_kg += collected_kg
            elif action is Action.MOVE and target is not None:
                total_moves += 1
            else:  # WAIT ou MOVE sem destino
                total_waits += 1

            # 4. Avanca o passo de tempo do agente (o act ja mexeu em
            #    current_sector/cleaned, mas nao em step).
            self.agent.state.step = step + 1

            history.append(
                StepRecord(
                    step=step,
                    sector=self.agent.state.current_sector,
                    action=action,
                    target=target,
                    collected_kg=collected_kg,
                    energy=self.agent.state.energy,
                )
            )
            last_step_index = step

            # 5. Checagens de parada.
            if self.agent.state.energy <= 0.0:
                depleted_energy = True
                break
            if step >= 5 and not self._has_any_waste():
                # Ambiente limpo (minimo de 5 passos para nao abortar
                # simulacoes muito pequenas).
                break

        final_energy = self.agent.state.energy
        energy_consumed = max(0.0, initial_energy - final_energy)
        reached_max = (
            last_step_index == cfg.max_steps - 1 and not depleted_energy
        )

        return SimulationResult(
            history=history,
            total_collected_kg=round(total_kg, 4),
            total_collections=total_collections,
            total_moves=total_moves,
            total_waits=total_waits,
            energy_consumed=round(energy_consumed, 4),
            final_energy=round(final_energy, 4),
            reached_max_steps=reached_max,
            depleted_energy=depleted_energy,
        )
