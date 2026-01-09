@echo off
REM Start script for MA-GET 3D React Simulation (Windows)

echo ====================================================
echo MA-GET 3D Logistics Simulation (React + Three.js)
echo ====================================================
echo.

REM Check if Python venv exists
if not exist "venv\" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate venv and install Python dependencies
echo Setting up Python backend...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM Check if node_modules exists in frontend
if not exist "frontend\node_modules\" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo Setup complete!
echo.
echo Starting services...
echo Backend API: http://localhost:8000
echo Frontend: http://localhost:3000
echo Press Ctrl+C to stop both services
echo.

REM Start backend in new window
start "Backend API" python backend.py

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
cd frontend
start "Frontend" npm start
cd ..

echo.
echo Both services started in separate windows!
echo Close both windows to stop the simulation.
pause
