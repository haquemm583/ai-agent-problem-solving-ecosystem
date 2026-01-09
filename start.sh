#!/bin/bash
# Quick start script for MA-GET 3D Simulation

echo "🌍 MA-GET 3D Logistics Simulation"
echo "=================================="
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
