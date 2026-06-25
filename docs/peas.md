# Questao 1.1 — Descricao PEAS do Agente de Logistica Reversa

> Documento de referencia para a Atividade MAPA de IA (Unicesumar).
> Mapeia cada item do acronimo PEAS para o componente do projeto
> que o implementa.

## P — Performance (Medida de Desempenho)

O agente eh avaliado por tres metricas primarias, todas computadas
em `logistica_reversa/reports/metrics.py::RunMetrics`:

| Objetivo | Metrica | Campo em `RunMetrics` |
|---|---|---|
| Maximizar volume processado | Residuos coletados (kg) | `collected_kg` |
| Minimizar gasto energetico | Energia consumida | `energy_consumed` |
| Reduzir tempo de operacao | Passos totais | `steps` |
| Equilibrio global | Eficiencia energetica (kg/u) | `efficiency` |

A eficiencia combina coleta e energia: `efficiency = collected_kg / energy_consumed`.
Quanto maior, melhor — eh a "nota final" do agente em um cenario.

## E — Environment (Ambiente)

O ambiente eh o centro de distribuicao automatizado modelado como
um **grafo nao-direcionado** em `logistica_reversa/environment/warehouse.py::Warehouse`.

- **Nos** do grafo = setores (salas) do centro. Coordenadas (x, y)
  definem a posicao espacial. Identificados por `sector_id: int`.
- **Arestas** = corredores entre setores, com `weight` (custo de
  atravessar).
- **Estado dos setores** = mutavel (`Sector.has_waste`,
  `Sector.cleaned_step`) — o ambiente pode ser alterado pela
  simulacao.
- **Residuos** = entidades congeladas (`Waste` em `domain/waste.py`)
  representando material a ser coletado.
- **Dinamica**: `deposit_random_waste` (acionado com probabilidade
  `deposit_prob` por passo) injeta novos residuos — comprovando que
  o ambiente eh **estocastico e dinamico**.

## A — Actuators (Atuadores)

Os atuadores estao abstraidos pelas acoes discretas do agente,
definidas em `logistica_reversa/agents/base.py::Action`:

| Acao (atuador) | Implementacao | Efeito real simulado |
|---|---|---|
| `MOVE` (locomocao) | `ModelBasedAgent.act()` quando o planejador retorna caminho | Consome `energy_per_step` e avanca para o proximo setor do plano |
| `COLLECT` (braco coletor) | `ModelBasedAgent.act()` quando `sector.has_waste` | Chama `Warehouse.collect_at()`, marca setor como limpo, consome `energy_per_collect` |
| `WAIT` (modo espera) | Quando nao ha setor alcancavel respeitando o cooldown | Preserva energia; usado quando a regra anti-retorno bloqueia todos os goals |

A camada `services/simulation.py::Simulation` traduz cada `Action`
retornada por `act()` em mutacoes de estado do ambiente.

## S — Sensors (Sensores)

Os sensores do robo sao modelados pela funcao `perceive()` em
`BaseAgent` e consumidos por `ModelBasedAgent.act()`:

| Sensor real | Modelagem no projeto | Onde aparece |
|---|---|---|
| Cameras / sensores opticos | `perceive(observation)` recebe a lista de setores com residuo visiveis | `agents/model_based.py:94` |
| Sensores de proximidade / mapa | `Warehouse.neighbors(sector_id)` retorna vizinhos ordenados | `environment/warehouse.py:91` |
| Sensores de carga | `RunMetrics.collected_kg` (kg coletados) | `reports/metrics.py` |
| Sensores energeticos | `AgentState.energy` e `RunMetrics.energy_consumed` | `domain/agent_state.py:33` e `reports/metrics.py` |
| Memoria interna (estado) | `AgentState.cleaned` registra a ultima limpeza por setor | `domain/agent_state.py:30` |

Alem dos sensores externos, o agente possui um **modelo interno**
(`AgentState`) que eh parte essencial de sua definicao como
"reativo baseado em modelo" — ver `docs/agente-baseado-em-modelo.md`.

## Resumo visual

```
+-----------------------------+    +--------------------------------+
|    AMBIENTE (Warehouse)     |    |   AGENTE (ModelBasedAgent)     |
|  - Grafo de setores         |<---|  perceive(): lista de setores  |
|  - Residuos dinamicos       |    |           com residuo          |
|  - Eventos estocasticos     |    |                                |
+-----------------------------+    |  act() -> Action:              |
         |                          |   - COLLECT se ha residuo      |
         |  muta estado             |   - MOVE via planejador        |
         |  (collect, deposit)      |   - WAIT se cooldown bloqueia  |
         v                          |                                |
+-----------------------------+    |  Estado interno (AgentState):  |
|  ATUADORES (Actions)        |--->|   - current_sector             |
|  - MOVE (locomocao)         |    |   - cleaned[sector] -> step    |
|  - COLLECT (coleta)         |    |   - step, energy, cooldown     |
|  - WAIT (espera)            |    +--------------------------------+
+-----------------------------+
```

## Onde cada item eh testado

| Componente | Teste |
|---|---|
| `RunMetrics` (Performance) | `tests/test_metrics.py` |
| `Warehouse` (Environment) | `tests/test_warehouse_io.py` + `tests/test_environment.py` |
| `Action` e `Simulation` (Actuators) | `tests/test_simulation.py` |
| `ModelBasedAgent` e `AgentState` (Sensors + estado interno) | `tests/test_agents.py` + `tests/test_agent_state.py` |
