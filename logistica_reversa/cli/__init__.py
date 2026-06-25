"""Camada de CLI.

Ponto de entrada para o usuario final. `parser.build_parser()`
retorna o `argparse.ArgumentParser` com os subcomandos `run`,
`compare` e `snapshot`. `parser.dispatch(args)` executa o
subcomando escolhido.
"""
from logistica_reversa.cli.parser import PLANNER_REGISTRY, build_parser, dispatch

__all__ = ["PLANNER_REGISTRY", "build_parser", "dispatch"]
