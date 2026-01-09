# MA-GET: Multi-Agent Generative Economic Twin for Logistics

A **3D Visual Simulation** of autonomous logistics negotiation with real-time API data integration, built with **React** and **Three.js**.

## 🎯 Overview

MA-GET is a modern 3D visualization platform that simulates a Texas-based logistics corridor where autonomous AI agents negotiate shipping contracts in real-time. The system uses **real-world data** from weather APIs, fuel price sources, and traffic conditions to create a realistic simulation environment.

### Key Features

- 🌍 **Beautiful 3D Visualization** using React Three Fiber and Three.js
- 🏢 **Realistic 3D Models** - buildings, trucks, and roads
- 🔴 **Single Button Control** - Start/Stop simulation with one click
- 🌦️ **Real Weather Data** from OpenWeatherMap API
- ⛽ **Live Fuel Prices** for different Texas cities
- 🚦 **Traffic Conditions** based on time-of-day and random incidents
- 🤖 **AI Agents** negotiating logistics contracts autonomously
- ⚡ **Modern Stack** - React, TypeScript, FastAPI, Three.js

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  MA-GET 3D SIMULATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │   React Frontend (TypeScript + Three.js)         │          │
│  │  ・Single START/STOP Button                      │          │
│  │  ・3D Scene with Buildings, Trucks, Roads        │          │
│  │  ・Real-time Stats Display                       │          │
│  │  ・Smooth Camera Controls                        │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   │ HTTP/REST API                               │
│                   ▼                                             │
│  ┌──────────────────────────────────────────────────┐          │
│  │   FastAPI Backend (Python)                       │          │
│  │  ・RESTful API Endpoints                         │          │
│  │  ・CORS Enabled                                  │          │
│  │  ・Real-time Data Serving                        │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   │                                             │
│                   ▼                                             │
│  ┌──────────────────────────────────────────────────┐          │
│  │   Real-time APIs & Data Integration              │          │
│  │  ・OpenWeatherMap (Weather)                      │          │
│  │  ・Fuel Price Data                               │          │
│  │  ・Traffic Simulation                            │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   │                                             │
│                   ▼                                             │
│  ┌──────────────────────────────────────────────────┐          │
│  │   WorldState (NetworkX Graph)                    │          │
│  │  ・5 Texas Cities (nodes)                        │          │
│  │  ・7 Routes (edges)                              │          │
│  │  ・Real-time Conditions                          │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   │                                             │
│                   ▼                                             │
│  ┌──────────────────────────────────────────────────┐          │
│  │   AI Agents (Autonomous)                         │          │
│  │  ・Warehouse Agents                              │          │
│  │  ・Carrier Agents                                │          │
│  │  ・Market Heartbeat                              │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 Technology Stack

### Frontend
- **React 18** - Modern UI framework
- **TypeScript** - Type-safe development
- **Three.js** - WebGL 3D rendering
- **React Three Fiber** - React renderer for Three.js
- **@react-three/drei** - Useful helpers for R3F
- **Axios** - HTTP client for API calls

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **NetworkX** - Graph-based world state
- **Requests** - API integration

### Data Sources
- **OpenWeatherMap API** - Real weather data
- **Custom** - Fuel prices and traffic simulation

## 📁 Project Structure

```
ai-agent-problem-solving-ecosystem/
├── main.py                      # Main orchestration & entry point
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── src/                         # Source code (modular structure)
│   ├── __init__.py
│   ├── agents/                  # Agent logic and behaviors
│   │   ├── __init__.py
│   │   └── agents.py           # Warehouse, Carrier, and Auditor agents
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── schema.py           # Pydantic models and data structures
│   │   ├── world.py            # NetworkX graph & environment
│   │   ├── marketplace.py      # Multi-carrier auction system
│   │   ├── market_heartbeat.py # Autonomous demand generation
│   │   └── deal_database.py    # Deal tracking & reputation system
│   ├── ui/                      # Dashboard and visualization
│   │   ├── __init__.py
│   │   ├── dashboard.py        # Streamlit 3D Mission Control
│   │   └── viz_components.py   # PyDeck 3D visualization layers
│   └── utils/                   # Utilities and helpers
│       ├── __init__.py
│       └── event_log.py        # Real-time event logging
├── tests/                       # Test files
│   ├── test_reputation.py
│   └── test_autonomous_features.py
└── docs/                        # Documentation
    ├── 3D_DASHBOARD_GUIDE.md
    ├── 3D_IMPLEMENTATION_SUMMARY.md
    ├── AUTONOMOUS_FEATURES_UPDATE.md
    ├── IMPLEMENTATION_SUMMARY.md
    ├── MARKETPLACE_UPDATE.md
    ├── QUICKSTART_3D.md
    ├── QUICKSTART_AUTONOMOUS.md
    └── REPUTATION_SYSTEM.md
```

## 🌐 Real Data Sources

The simulation integrates with the following real-world data sources:

### Weather API (OpenWeatherMap)
- **Free Tier**: 1,000 calls/day
- **Data**: Temperature, wind speed, weather conditions
- **Updates**: Real-time weather affecting route conditions
- **Signup**: https://openweathermap.org/api

### Fuel Prices
- City-specific fuel prices based on Texas market data
- Daily variations reflecting market conditions
- Lower prices near refineries (Houston, Corpus Christi)

### Traffic Conditions
- Time-of-day based congestion (rush hour: 6-9 AM, 4-7 PM)
- Random incident generation (5% probability)
- Route closures for severe incidents

## 🎨 3D Visualization Features

The simulation uses **React Three Fiber** and **Three.js** for stunning 3D graphics:

- 🏢 **3D Buildings**: Warehouses represented as realistic 3D structures
  - Height varies based on inventory levels
  - Color indicates capacity: Green (<30%), Yellow (30-70%), Red (>70%)
  - Subtle breathing animation for visual interest
  
- 🚚 **Animated Trucks**: Realistic delivery vehicles
  - Move along routes between warehouses
  - Appear/disappear based on active shipments
  - Smooth interpolation for natural movement

- 🛣️ **Route Network**: Visual connections between cities
  - Green lines for open routes
  - Red lines for closed/blocked routes
  - Width indicates traffic volume

- 🎮 **Interactive Controls**:
  - **Orbit**: Click and drag to rotate view
  - **Zoom**: Scroll to zoom in/out
  - **Pan**: Right-click and drag to pan
  - **Auto-rotate**: Optional automatic camera rotation

- 💡 **Dynamic Lighting**:
  - Ambient lighting for overall visibility
  - Directional light for shadows
  - Point lights for highlights

## 🚀 Quick Start

### Method 1: Quick Start Scripts (Recommended)

**Linux/Mac:**
```bash
./start-react.sh
```

**Windows:**
```bash
start-react.bat
```

These scripts will automatically:
- Create a Python virtual environment
- Install all backend dependencies
- Install all frontend (Node.js) dependencies
- Launch the FastAPI backend server
- Launch the React development server
- Open the simulation in your browser

### Method 2: Manual Setup

#### Prerequisites
- Python 3.8+
- Node.js 16+ and npm

#### 1. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install
```

#### 3. Configure API Keys (Optional)

Copy `.env.template` to `.env` and add your OpenWeatherMap API key for real weather data:

```bash
cp .env.template .env
# Edit .env and add your OPENWEATHER_API_KEY
```

Get a free API key at: https://openweathermap.org/api (1000 calls/day free tier)

**Note**: The simulation works without an API key using realistic mock data.

#### 4. Run the Simulation

**Terminal 1 - Backend:**
```bash
python backend.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

The simulation will open at `http://localhost:3000`

### 5. Control the Simulation

- Click **▶ START** to begin the simulation
- Click **⏸ STOP** to pause the simulation
- Use mouse to orbit, zoom, and pan the 3D view
- Watch trucks move between warehouses in real-time!

## 🗺️ Texas Logistics Corridor

The simulation models 5 major Texas cities connected by highways:

| City | Warehouse Capacity | Initial Inventory |
|------|-------------------|-------------------|
| Corpus Christi | 2,000 | 800 |
| Houston | 5,000 | 2,000 |
| Austin | 3,000 | 1,200 |
| San Antonio | 3,500 | 1,500 |
| Dallas | 4,500 | 1,800 |

### Route Network

```
                    Dallas
                   ╱     ╲
              195mi       239mi
                ╱           ╲
            Austin ─────── Houston
              │    165mi     │
             80mi           197mi
              │              │
         San Antonio ───────┘
              │
            143mi
              │
        Corpus Christi ─── Houston
                    210mi
```

## 🤖 How It Works

### 1. Real Data Collection
The simulation pulls live data from APIs:
- Weather conditions for each Texas city
- Fuel prices with city-specific variations
- Traffic conditions based on time and random incidents

### 2. World State Updates
Data is applied to the NetworkX graph:
- Route conditions updated based on weather
- Fuel costs adjusted by traffic congestion
- Routes may close due to severe incidents

### 3. Agent Negotiations
AI agents autonomously:
- Generate shipping orders based on inventory levels
- Compete for contracts through marketplace bidding
- Make decisions based on real-time conditions

### 4. 3D Visualization
PyDeck renders the network in real-time:
- Inventory levels shown as 3D columns
- Routes displayed as arcs with varying conditions
- Updates every simulation tick (2 seconds)

## 💡 Usage Tips

- **Start Simple**: Click START and watch the simulation run
- **API Key Optional**: Works without OpenWeather API key (uses mock data)
- **Performance**: Smooth on modern browsers with WebGL support
- **Data Accuracy**: With API key, weather updates every few seconds
- **Simulation Speed**: Adjustable in code (default: 2 second ticks)

## 📈 Current Features

### 3D Visualization
- ✅ **PyDeck 3D rendering** with interactive visualization
- ✅ **Real-time updates** reflecting live API data
- ✅ **Inventory visualization** with 3D columns
- ✅ **Route network** showing connections and conditions
- ✅ **Single button interface** for simple control

### Real Data Integration
- ✅ **OpenWeatherMap API** for live weather conditions
- ✅ **Fuel price data** with city-specific variations
- ✅ **Traffic conditions** based on time-of-day and random incidents
- ✅ **Automatic fallback** to mock data if APIs unavailable

### AI Agent System
- ✅ Autonomous warehouse and carrier agents
- ✅ Multi-carrier marketplace with competitive bidding
- ✅ Reputation tracking system
- ✅ Real-time negotiation and contract awards

## 📁 Project Structure

```
ai-agent-problem-solving-ecosystem/
├── backend.py                   # FastAPI server for React frontend
├── app.py                       # Legacy Streamlit app (deprecated)
├── main.py                      # CLI interface (optional)
├── start-react.sh               # Quick start for Linux/Mac
├── start-react.bat              # Quick start for Windows
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── frontend/                    # React + Three.js application
│   ├── public/
│   ├── src/
│   │   ├── App.tsx             # Main React component
│   │   ├── App.css             # Styles
│   │   └── index.tsx           # Entry point
│   ├── package.json            # Node.js dependencies
│   └── tsconfig.json           # TypeScript configuration
├── src/
│   ├── core/
│   │   ├── api_integrations.py # Real API data fetching
│   │   ├── world.py            # NetworkX world state
│   │   ├── marketplace.py      # Multi-carrier auctions
│   │   └── schema.py           # Pydantic models
│   ├── agents/
│   │   └── agents.py           # AI agent behaviors
│   └── utils/
│       └── event_log.py        # Event logging
├── tests/                       # Test files
└── docs/                        # Documentation
```

## 🎓 Learn More

### API Documentation
- Backend API docs available at: `http://localhost:8000/docs` (when running)
- Interactive API testing with Swagger UI

### For detailed technical documentation, see:
- **docs/3D_SIMULATION_RESTRUCTURE.md** - Implementation details
- **docs/3D_IMPLEMENTATION_SUMMARY.md** - Technical architecture
- **docs/MARKETPLACE_UPDATE.md** - Multi-agent marketplace details

### Technology Documentation
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber) - React renderer for Three.js
- [Three.js](https://threejs.org/docs/) - 3D graphics library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

## 📝 License

MIT License - See LICENSE file for details.

---

**Built with**: React, TypeScript, Three.js, FastAPI, Python, OpenWeatherMap API  
**Author**: Solo developer project for learning and experimentation
