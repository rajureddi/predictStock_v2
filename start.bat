@echo off
cd /d "%~dp0"

echo ===================================================
echo Starting MarketMind Pro Backend and Frontend
echo ===================================================

:: Start Backend
if exist ".venv\Scripts\activate.bat" (
    start "MarketMind Backend (Port 8001)" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --app-dir backend --port 8001 --reload"
) else (
    start "MarketMind Backend (Port 8001)" cmd /k "uvicorn app.main:app --app-dir backend --port 8001 --reload"
)

:: Start Frontend
start "MarketMind Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Services launched in separate terminal windows!
echo - Backend:  http://localhost:8001
echo - Frontend: http://localhost:5174
echo.
