# Questao 1.3 — Agente Reativo Baseado em Modelo

> Documento de referencia para a Atividade MAPA de IA (Unicesumar).
> Em vez de transcrever um pseudocodigo didatico, esta pagina
> apresenta o **codigo real** do agente e explica como cada linha
> atende ao requisito de "estado interno + regra anti-retorno
> com cooldown T".

## Visão geral

O agente implementado em `logistica_reversa/agents/model_based.py`
eh um **Agente Reativo Baseado em Modelo**: combina percepcoes
atuais (setores com residuo) com um modelo interno do mundo
(`AgentState`) para decidir a proxima acao.

| Componente | Arquivo | Linhas |
|---|---|---|
| Loop `perceive -> act` | `agents/model_based.py` | 94–164 |
| Estado interno (modelo) | `domain/agent_state.py` | 15–76 |
| Regra anti-retorno (cooldown T) | `domain/agent_state.py` | 35–48 |
| Acoes discretas (atuadores) | `agents/base.py` | `Action` enum |
| Planejador (default: A*) | `search/astar.py` + `search/heuristics.py` | — |

## Codigo-fonte do `act()`

O metodo abaixo **eh** a implementacao real do pseudocodigo
"Agente Reativo Baseado em Modelo com regra anti-retorno":

```python
# logistica_reversa/agents/model_based.py:106-164
def act(self) -> Action:
    """Decide a proxima acao (COLLECT, MOVE ou WAIT)."""
    current = self.state.current_sector
    sector = self._warehouse.get_sector(current)

    # Regra 1: se ha residuo aqui, coleta antes de planejar.
    if sector.has_waste:
        self._warehouse.collect_at(current, self.state.step)
        self.state.mark_cleaned(current)
        self.state.consume_energy(self._energy_per_collect)
        self.last_action = Action.COLLECT
        self.last_move_target = None
        return self.last_action

    # Regra 2: filtra goals pela regra anti-retorno.
    goals_in_world = self._warehouse.sectors_with_waste()
    allowed = [g for g in goals_in_world if self.state.can_return(g)]

    if not allowed:
        self.last_action = Action.WAIT
        self.last_move_target = None
        return self.last_action

    # Regra 3-4: planeja ate o goal mais proximo.
    problem = build_problem_from_warehouse(
        self._warehouse,
        initial_state=current,
        goals=allowed,
    )
    goal_node = self._planner(problem, heuristic=self._heuristic)
    if goal_node is None:
        self.last_action = Action.WAIT
        self.last_move_target = None
        return self.last_action

    path = goal_node.path()
    if len(path) < 2:
        self.last_action = Action.WAIT
        self.last_move_target = None
        return self.last_action

    # Regra 5: caminha para o proximo no do caminho.
    next_sector = path[1].state
    self.state.move_to(next_sector)
    self.state.consume_energy(self._energy_per_step)
    self.last_action = Action.MOVE
    self.last_move_target = next_sector
    return self.last_action
```

## Estado interno (`AgentState`)

O modelo interno sustenta a regra anti-retorno. O trecho abaixo
**eh** o "estado_inicial {}" e "tempo_limite T" do pseudocodigo
tradicional:

```python
# logistica_reversa/domain/agent_state.py:15-48
@dataclass
class AgentState:
    current_sector: int
    cleaned: dict[int, int] = field(default_factory=dict)
    step: int = 0
    cooldown: int = 3         # <-- T, passos minimos antes de revisitar
    energy: float = 100.0

    def can_return(self, sector_id: int) -> bool:
        """Verifica se o agente pode retornar respeitando o cooldown."""
        last_cleaned = self.cleaned.get(sector_id)
        if last_cleaned is None:
            return True
        return (self.step - last_cleaned) >= self.cooldown
```

`cooldown` eh o parametro **T** que a Questao 1.3 pede para
impedir que o robo retorne a uma sala ja limpa antes de um tempo
determinado.

## Mapeamento entre pseudocodigo do enunciado e codigo real

| Pseudocodigo (enunciado) | Codigo real |
|---|---|
| `INICIALIZAR estado_interno <- {}` | `AgentState.cleaned = {}` no `__init__` |
| `INICIALIZAR tempo_limite <- T` | `AgentState.cooldown = T` (default 3) |
| `ATUALIZAR estado_interno[setor_atual] <- tempo_atual` | `state.mark_cleaned(current)` em `act()` |
| `SE sensor_residuos = "presente": COLETAR` | `if sector.has_waste: ... Action.COLLECT` |
| `SE (tempo_atual - estado_interno[setor]) < T: IGNORAR / MOVER` | `allowed = [g for g in goals_in_world if self.state.can_return(g)]` |
| `SENAO: REVISITAR setor_atual` | Setor aparece em `allowed` apenas se `can_return` for True |
| `SE energia < limiar: RETORNAR base` | `consume_energy` reduz `state.energy` a cada passo/coleta |

A unica diferenca mecanica eh que o pseudocodigo do enunciado
lista "retornar a base" como caso separado; no projeto, a regra
anti-retorno + `WAIT` cumprem o mesmo papel: o agente para de
gastar energia quando nao ha goal alcancavel.

## Por que esse agente e' baseado em modelo

- **Reativo**: cada acao depende apenas do estado atual do
  ambiente + estado interno (sem deliberacao sobre o futuro
  alem do proximo passo do planejador).
- **Baseado em modelo**: a funcao `state.can_return(g)` consulta
  `state.cleaned` e `state.step` — informacoes que o ambiente
  **nao fornece diretamente**. Sem o modelo, o agente nao
  saberia a quanto tempo limpou cada setor.

## Onde cada parte e' testada

| Comportamento | Teste |
|---|---|
| `cooldown` bloqueia revisita prematura | `tests/test_agent_state.py::TestCanReturn` |
| `mark_cleaned` atualiza o passo | `tests/test_agent_state.py::TestMarkCleaned` |
| `act()` retorna `COLLECT` quando ha residuo | `tests/test_agents.py::TestModelBasedAgent` |
| `act()` chama o planejador quando nao ha residuo | `tests/test_agents.py::TestModelBasedAgent::test_uses_planner` |
| Simulacao fim-a-fim com anti-retorno | `tests/test_simulation.py::TestSimulationRun` |
