#!/usr/bin/env bash
# Helper para Linux/macOS. Ativa o venv (se existir) e roda uma simulacao.
# Uso: ./run.sh [argumentos extras para `python main.py run`]

set -e

if [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python main.py run --rows 5 --cols 5 --output-dir pipeline-outputs "$@"
