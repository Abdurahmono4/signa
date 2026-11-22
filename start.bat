@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found: .venv
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
if errorlevel 1 (
  echo SignBridge startup failed. Check storage\runs logs.
  pause
  exit /b 1
)
