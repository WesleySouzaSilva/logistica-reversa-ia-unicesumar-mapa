# Logística Reversa — Agentes Inteligentes (Unicesumar)

Projeto da Atividade MAPA de Inteligência Artificial — implementação completa que cobre os conceitos de **PEAS**, **classificação de ambientes**, **agentes reativos baseados em modelo** e **algoritmos de busca** (BFS, DFS, UCS, Greedy, A*) com visualização gráfica.

> **Status**: 8/8 PRs entregues. Implementação completa.

---

## O que o projeto demonstra

| Conceito (Russel & Norvig) | Onde está implementado |
|---|---|
| PEAS (Performance, Environment, Actuators, Sensors) | `domain/` + `agents/` |
| Ambiente parcialmente observável, dinâmico, estocástico, sequencial | `environment/warehouse.py` (eventos dinâmicos) |
| Agente baseado em modelo (ModelBasedAgent) com planejador A* e regra anti-retorno | `agents/model_based.py` |
| Algoritmos de busca (BFS, DFS, UCS, Greedy, A*) | `search/` |
| Heurísticas h(n) admissíveis (Manhattan, Euclidiana) | `search/heuristics.py` |
| Métricas comparativas | `reports/metrics.py` |
| Visualização com networkx + matplotlib | `visualization/plotter.py` |

---

## Como rodar (Windows / Linux / macOS)

> Dependências declaradas em `requirements.txt`:
> - `networkx>=3.0` — modelagem do grafo do armazém
> - `matplotlib>=3.5` — visualização da trajetória
> - `pandas>=1.5` — tabelas comparativas
> - `pytest>=7.0` — testes

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

> Requisito: Python ≥ 3.10.

---

## Como usar a CLI

A interface de linha de comando oferece quatro subcomandos:

```bash
# 1. Executa UMA simulacao e gera os artefatos (metrics, PNG, run.json).
python main.py run --rows 5 --cols 5 --max-steps 200 --seed 42 --planner astar

# 2. Compara varios planejadores e gera uma tabela comparativa.
python main.py compare --planners astar bfs --max-steps 100

# 3. Salva a topologia vazia de uma grade em JSON para reutilizacao.
python main.py snapshot --rows 5 --cols 5 --out data/warehouse.json

# 4. Agrega N `metrics.csv` de corridas previas em um relatorio final.
python main.py report --run-dirs pipeline-outputs/run1 pipeline-outputs/run2
```

Saídas geradas (em `pipeline-outputs/` por padrão):

| Arquivo | Conteúdo |
|---|---|
| `metrics.md` / `metrics.csv` | Tabela de uma linha com kg, coletas, energia, eficiência (PEAS) |
| `warehouse.png` | Grafo do armazém colorido por estado + trajetória do agente |
| `run.json` | Snapshot da configuração (reprodutibilidade) |
| `comparison.md` / `comparison.csv` | Tabela multi-linha (apenas no `compare`) |
| `relatorio-final.md` / `relatorio-final.csv` | Tabela agregada de N corridas (apenas no `report`) |

Atalhos prontos: `./run.sh` (Linux/macOS) ou `run.bat` (Windows) executam `python main.py run --rows 5 --cols 5`.

---

## Respostas da Questão 1 (MAPA)

### 1.1 — Descrição PEAS

| Componente | Descrição |
|---|---|
| **P**erformance | Volume de material processado (kg) / energia gasta — `eficiencia = coleta / energia` |
| **E**nvironment | Centro de distribuição com N setores; parcialmente observável, dinâmico, estocástico, sequencial |
| **A**ctuators | Motores de locomoção, braço coletor, sinalizador de status |
| **S**ensors | Sensor de presença de resíduo (tipo + peso), odômetro, sensor de bateria |

### 1.2 — Classificação do Ambiente

| Propriedade | Valor | Justificativa |
|---|---|---|
| Observabilidade | **Parcial** | O robô vê apenas o setor atual + adjacentes |
| Determinismo | **Estocástico** | Novos resíduos aparecem aleatoriamente |
| Episodicidade | **Sequencial** | Decisão atual afeta as próximas (energia, setores visitados) |
| Estaticidade | **Dinâmico** | Ambiente muda enquanto o agente decide |
| Discretude | **Discreto** | Conjunto finito de setores e ações |

### 1.3 — Pseudocódigo do Agente Reativo Baseado em Modelo

```text
FUNÇÃO agente_baseado_em_modelo(percepção):
    estado_interno.atualizar(percepção)
    setor_atual = estado_interno.setor_atual

    # Ação reativa: coleta se há resíduo
    SE setor_atual tem_resíduo:
        estado_interno.marcar_limpo(setor_atual, passo_atual)
        RETORNAR None  # ação local: coletar

    # Usa modelo interno para decidir próximo setor
    candidatos = vizinhos(setor_atual)

    # Regra anti-retorno (preserva autonomia energética):
    # não volta a setor recém-limpo antes de T passos
    candidatos = [c para c em candidatos
                  SE estado_interno.pode_retornar(c, passo_atual, T)]

    SE candidatos vazio:
        RETORNAR None  # espera novo evento

    próximo = argmax(candidatos, key=peso_resíduo)
    estado_interno.mover(próximo)
    RETORNAR próximo
```

---

## Estrutura do projeto (Clean Architecture)

```
logistica_reversa/
├── main.py                  CLI argparse
├── domain/                  Modelos puros (enums, dataclasses)
├── environment/             Grafo + eventos dinâmicos
├── search/                  BFS, DFS, UCS, Greedy, A*, heurísticas
├── agents/                  Agente baseado em modelo
├── services/                Simulação
├── reports/                 Métricas com pandas
├── visualization/           Matplotlib
├── data/                    JSON do armazém
└── tests/                   Pytest
```

### Decisões de engenharia (por que essa estrutura?)

1. **Clean Architecture** — `domain` não depende de nada; agentes e buscas dependem só dele. Testável sem framework.
2. **Strategy Pattern** — `BaseAgent` permite trocar algoritmo de decisão sem mudar a simulação.
3. **Open/Closed** — adicionar novo agente = novo arquivo, sem mexer no que existe.
4. **Inversão de dependência** — `Simulation` depende de `BaseAgent`, não de classe concreta.
5. **Princípio da Responsabilidade Única** — cada módulo tem UMA razão para mudar.

---

## Plano de PRs

| # | Conteúdo |
|---|---|
| 1 | Documentação inicial + `requirements.txt` + `.gitignore` (este PR) |
| 2 | `domain/` (enums, dataclasses) + testes |
| 3 | `environment/` (grafo do armazém + gerador) + testes |
| 4 | `search/` (BFS, DFS, UCS, Greedy, A*, heurísticas) + testes |
| 5 | `agents/` (ModelBasedAgent com A* + regra anti-retorno) + testes |
| 6 | `services/simulation.py` + `reports/metrics.py` + testes |
| 7 | `visualization/plotter.py` + `main.py` (CLI) + `data/warehouse.json` + scripts |
| 8 | README final + validação completa |

---

## Referência

RUSSELL, S.; NORVIG, P. *Artificial Intelligence: A Modern Approach*. 4ª ed. Pearson, 2020.
JUNIOR, M. M. C. *Inteligência Artificial*. Maringá: Unicesumar, 2022.