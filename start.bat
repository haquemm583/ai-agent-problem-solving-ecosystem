@echo off
REM LEGACY: Streamlit version startup script (Windows)
REM For the new React + Three.js version, use: start-react.bat

echo ================================
echo LEGACY VERSION
echo ================================
echo MA-GET 3D Logistics Simulation
echo ================================
echo.
echo NOTE: You are starting the legacy Streamlit version.
echo For the new React + Three.js version with better graphics,
echo use: start-react.bat
echo.
pause
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
