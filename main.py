"""Ponto de entrada da CLI.

Uso:
    python main.py run --rows 5 --cols 5 --output-dir pipeline-outputs
    python main.py compare --planners astar bfs
    python main.py snapshot --rows 4 --cols 4 --out data/warehouse.json

Toda a logica de parsing vive em `logistica_reversa.cli.parser`.
Este arquivo eh apenas o shim que `run.bat` / `run.sh` invocam.
"""
from __future__ import annotations

import sys

from logistica_reversa.cli.parser import dispatch


def main() -> int:
    return dispatch()


if __name__ == "__main__":
    sys.exit(main())
