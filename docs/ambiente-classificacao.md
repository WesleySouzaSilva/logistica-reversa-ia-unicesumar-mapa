# Questao 1.2 — Classificacao do Ambiente

> Documento de referencia para a Atividade MAPA de IA (Unicesumar).
> Classifica o ambiente do agente de logistica reversa nas cinco
> dimensoes de Russell & Norvig, justificando cada escolha com
> trechos do codigo real.

## Visao geral

| Dimensao | Classificacao | Resumo da justificativa |
|---|---|---|
| Observabilidade | **Parcialmente observavel** | O robo recebe a lista de setores com residuo, nao o mapa global |
| Determinismo | **Nao deterministico (estocastico)** | `deposit_random_waste` injeta residuos a cada passo com probabilidade `p` |
| Episodicidade | **Sequencial** | Decisao atual depende de estado interno (setores limpos, cooldown) |
| Estaticidade | **Dinamico** | Residuos aparecem enquanto o agente opera |
| Discretude | **Discreto** | Setores inteiros, acoes enumeradas, tempo em passos |

---

## 1. Observabilidade: Parcialmente observavel

**Definicao**: o agente nao tem acesso ao estado completo do ambiente
em um unico instante.

**Evidencia no codigo**: o metodo `perceive()` em
`logistica_reversa/agents/base.py` recebe apenas uma lista de
identificadores de setores com residuo, nao o estado global:

```python
# logistica_reversa/agents/model_based.py:94
def perceive(self, observation: list[int]) -> None:
    """Armazena a percepcao para uso no proximo `act`."""
    self._last_observation = list(observation)
```

O agente **nao** recebe de uma vez:
- a posicao de todos os residuos (apenas uma "amostra"),
- o estado dos setores distantes,
- o conteudo do grafo alem dos vizinhos imediatos (`Warehouse.neighbors()`).

O conjunto de vizinhos eh a unica informacao espacial completa que
o agente tem a cada passo. Para alcancar residuos distantes, ele
constrói um **modelo interno** (`AgentState`) e usa um planejador
da camada `search/` — exatamente o que define um agente baseado em
modelo em um ambiente parcialmente observavel.

## 2. Determinismo: Nao deterministico

**Definicao**: o proximo estado do ambiente nao eh completamente
determinado pelo estado atual e pela acao do agente.

**Evidencia no codigo**: a funcao `Warehouse.deposit_random_waste()`
eh chamada dentro do loop de `Simulation` com probabilidade
configuravel (`deposit_prob`):

```python
# logistica_reversa/services/simulation.py (trecho)
if rng.random() < self.config.deposit_prob:
    self.warehouse.deposit_random_waste(rng)
```

Isso significa que, apos o agente limpar um setor, novos residuos
podem surgir **sem que ele tenha agido**. O resultado de uma
simulacao depende da sequencia aleatoria gerada (controlada por
`seed` para reprodutibilidade — o que nao elimina o nao-determinismo,
apenas o torna observavel).

## 3. Episodicidade: Sequencial

**Definicao**: a decisao atual depende de decisoes anteriores.

**Evidencia no codigo**: o atributo `AgentState.cleaned` (mapa
`setor_id -> passo`) eh essencial para o funcionamento do agente:

```python
# logistica_reversa/domain/agent_state.py:30
cleaned: dict[int, int] = field(default_factory=dict)
```

A regra anti-retorno usa esse historico para decidir se o agente
**pode** voltar a um setor:

```python
# logistica_reversa/domain/agent_state.py:35
def can_return(self, sector_id: int) -> bool:
    last_cleaned = self.cleaned.get(sector_id)
    if last_cleaned is None:
        return True
    return (self.step - last_cleaned) >= self.cooldown
```

Sem esse historico, a regra do cooldown (T passos antes de
revisitar) seria impossivel. Como a decisao em `t` depende de
`cleaned[setor]` registrado em `t' < t`, o episodio eh
**sequencial**.

## 4. Estaticidade: Dinamico

**Definicao**: o ambiente pode mudar enquanto o agente delibera.

**Evidencia no codigo**: alem do `deposit_random_waste` ja citado,
a propria funcao `perceive()` declara explicitamente que a percepcao
pode ficar desatualizada:

```python
# logistica_reversa/agents/model_based.py:99
"""observation: lista de ids de setores com residuo.
A percepcao eh validada contra o mundo real no
momento do `act` (o ambiente pode ter mudado)."""
```

Ou seja: o ambiente se altera **durante a deliberação** do agente
(entre `perceive` e `act`). Isso impede estrategias baseadas apenas
em planejamentos rigidos e justifica o uso de replanejamento a
cada passo, que eh o que `ModelBasedAgent.act()` faz.

## 5. Discretude: Discreto

**Definicao**: o numero de estados do ambiente eh finito/enumeravel
e o tempo avanc̦a em passos discretos.

**Evidencia no codigo**:

- **Estados**: `sector_id: int`, `Sector.has_waste: bool`,
  `Sector.cleaned_step: Optional[int]`, `Waste.type: WasteType`
  (enum) — todos discretos.
- **Acoes**: `Action.MOVE | Action.COLLECT | Action.WAIT` — enum
  finito em `logistica_reversa/agents/base.py`.
- **Tempo**: a simulacao avanca em `step += 1` por iteracao
  (`AgentState.move_to`); nao ha tempo continuo.

Nao ha variaveis continuas relevantes para o agente (velocidade,
angulo de virada, etc. sao abstraidos em custo `weight` da aresta
— ainda discreto).

## Consequencia para o tipo de agente

A combinacao **parcialmente observavel + dinamico + sequencial**
exclui agentes puramente reativos (que reagiam apenas a percepcoes
imediatas) e justifica a escolha de um **Agente Reativo Baseado em
Modelo** (Questao 1.3 — ver `docs/agente-baseado-em-modelo.md`).
