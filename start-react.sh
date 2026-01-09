#!/bin/bash
# Start script for MA-GET 3D React Simulation

echo "🌍 MA-GET 3D Logistics Simulation (React + Three.js)"
echo "===================================================="
echo ""

# Check if Python venv exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv and install Python dependencies
echo "Setting up Python backend..."
source venv/bin/activate
pip install -q -r requirements.txt

# Check if node_modules exists in frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting services..."
echo "➡️  Backend API: http://localhost:8000"
echo "➡️  Frontend: http://localhost:3000"
echo "➡️  Press Ctrl+C to stop both services"
echo ""

# Start backend in background
python backend.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
cd frontend
npm start &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
