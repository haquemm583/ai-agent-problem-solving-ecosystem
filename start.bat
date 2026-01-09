@echo off
REM Quick start script for MA-GET 3D Simulation (Windows)

echo ================================
echo MA-GET 3D Logistics Simulation
echo ================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo Setup complete!
echo.
echo Starting 3D simulation...
echo The app will open in your browser
echo Click START to begin the simulation
echo Press Ctrl+C to stop
echo.

REM Run the app
streamlit run app.py
