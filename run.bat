@echo off
REM Helper para Windows. Ativa o venv (se existir) e roda uma simulacao.
REM Uso: run.bat [argumentos extras para `python main.py run`]

setlocal
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python main.py run --rows 5 --cols 5 --output-dir pipeline-outputs %*
endlocal
