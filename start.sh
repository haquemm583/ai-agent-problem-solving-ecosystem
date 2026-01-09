#!/bin/bash
# LEGACY: Streamlit version startup script
# For the new React + Three.js version, use: ./start-react.sh

echo "⚠️  LEGACY VERSION"
echo "================================"
echo "MA-GET 3D Logistics Simulation"
echo "================================"
echo ""
echo "NOTE: You are starting the legacy Streamlit version."
echo "For the new React + Three.js version with better graphics,"
echo "use: ./start-react.sh"
echo ""
read -p "Press Enter to continue with legacy version or Ctrl+C to cancel..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting 3D simulation..."
echo "➡️  The app will open in your browser"
echo "➡️  Click START to begin the simulation"
echo "➡️  Press Ctrl+C to stop"
echo ""

# Run the app
streamlit run app.py
