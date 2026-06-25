"""Regenerate docs/example/warehouse.png using the FINAL-state warehouse.

The CLI's `run` subcommand reloads a clean warehouse before plotting
(see logistica_reversa/cli/parser.py:134), which is why the stock
`python main.py run` image never shows green (has_waste) nodes.

This script keeps the same simulation but plots the post-run warehouse,
so the resulting PNG displays ALL legend elements: green (waste
remaining), gray (empty), red trajectory line, blue-bordered final
sector.
"""
from logistica_reversa.environment import generate_grid_warehouse
from logistica_reversa.agents.model_based import ModelBasedAgent
from logistica_reversa.search import astar_search
from logistica_reversa.services.simulation import Simulation, SimulationConfig
from logistica_reversa.visualization.plotter import plot_warehouse_graph

# 5x5 grid, start at sector 11 (middle-left).
wh = generate_grid_warehouse(n_rows=5, n_cols=5)
agent = ModelBasedAgent(warehouse=wh, initial_sector=11, planner=astar_search)

# Few steps + zero deposit_prob + high initial waste fraction -> the
# agent only manages a couple of collections, leaving plenty of waste
# on the board at the end so green nodes are visible in the plot.
cfg = SimulationConfig(
    max_steps=4,
    deposit_prob=0.0,
    seed=3,
    initial_waste_fraction=0.4,
)
result = Simulation(wh, agent, cfg).run()

print("residuos finais:", wh.sectors_with_waste())
print("setor final:", result.history[-1].sector)
print("trajetoria:", [h.sector for h in result.history])

out = plot_warehouse_graph(
    wh,
    result.history,
    output_path="docs/example/warehouse.png",
    title="Trajetoria - ASTAR (seed=3)",
)
print("PNG salvo em:", out)