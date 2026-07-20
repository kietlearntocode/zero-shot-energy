@echo off
echo ===================================================
echo Starting Ember Electricity Price Forecast System
echo ===================================================
echo.

echo [1/2] Starting Backend (FastAPI) in a new window...
start "Backend - FastAPI" cmd /k ".\venv\Scripts\activate && cd web_app\api_server && uvicorn main:app --reload --port 8000"

echo [2/2] Starting Frontend (Vue) in a new window...
start "Frontend - Vue/Vite" cmd /k "cd web_app\ui_client && npm run dev"

echo.
echo Complete! Please wait a few seconds for the servers to initialize.
echo Then, open your browser and navigate to: http://localhost:5173
echo.
pause
