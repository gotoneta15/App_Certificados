@echo off
REM Arranca la app de certificados de Academia Horizonte con doble clic.
cd /d "%~dp0"
uv run python app.py
pause
