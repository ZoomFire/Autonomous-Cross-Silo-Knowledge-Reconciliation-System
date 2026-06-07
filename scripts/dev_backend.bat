@echo off
cd /d "%~dp0..\backend"
set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
