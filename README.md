# MA-GET: Multi-Agent Generative Economic Twin for Logistics

A **3D Visual Simulation** of autonomous logistics negotiation with real-time API data integration.

## 🎯 Overview

MA-GET is a 3D visualization platform that simulates a Texas-based logistics corridor where autonomous AI agents negotiate shipping contracts in real-time. The system uses **real-world data** from weather APIs, fuel price sources, and traffic conditions to create a realistic simulation environment.

### Key Features

- 🌍 **3D Interactive Visualization** using PyDeck rendering
- 🔴 **Single Button Control** - Start/Stop simulation with one click
- 🌦️ **Real Weather Data** from OpenWeatherMap API
- ⛽ **Live Fuel Prices** for different Texas cities
- 🚦 **Traffic Conditions** based on time-of-day and random incidents
- 🤖 **AI Agents** negotiating logistics contracts autonomously

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MA-GET 3D SIMULATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐            │
│  │   Real-time APIs │         │  3D Visualization│            │
│  │  ・Weather        │────────▶│   (PyDeck)       │            │
│  │  ・Fuel Prices   │         │                  │            │
│  │  ・Traffic Data  │         │  Single Button   │            │
│  └──────────────────┘         │  START / STOP    │            │
│           │                   └──────────────────┘            │
│           ▼                                                    │
│  ┌──────────────────┐                                         │
│  │   WORLD STATE    │                                         │
│  │  (NetworkX Graph)│◄──────┐                                │
│  │  ・Cities        │        │                                │
│  │  ・Routes        │   ┌────┴─────────┐                     │
│  │  ・Conditions    │   │  AI Agents   │                     │
│  └──────────────────┘   │ ・Warehouse  │                     │
│                         │ ・Carrier    │                     │
│                         └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

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

The simulation uses **PyDeck** for high-performance 3D rendering:

- 🏢 **3D Inventory Columns**: Height represents warehouse stock levels
- 🛣️ **Route Network**: Arcs showing connections between cities
- 🌈 **Color Coding**:
  - Green inventory: <30% capacity
  - Yellow inventory: 30-70% capacity
  - Red inventory: >70% capacity
- 🔄 **Real-time Updates**: Visualization updates as simulation runs

## 🚀 Quick Start

### Method 1: Quick Start Scripts (Recommended)

**Linux/Mac:**
```bash
./start.sh
```

**Windows:**
```bash
start.bat
```

These scripts will automatically:
- Create a virtual environment
- Install all dependencies
- Launch the 3D simulation

### Method 2: Manual Setup

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Configure API Keys (Optional)

Copy `.env.template` to `.env` and add your OpenWeatherMap API key for real weather data:

```bash
cp .env.template .env
# Edit .env and add your OPENWEATHER_API_KEY
```

Get a free API key at: https://openweathermap.org/api (1000 calls/day free tier)

**Note**: The simulation works without an API key using realistic mock data.

#### 3. Run the 3D Simulation

```bash
streamlit run app.py
```

This will launch the 3D visualization in your browser with a single START/STOP button.

### 4. Control the Simulation

- Click **▶ START** to begin the simulation
- Click **⏸ STOP** to pause the simulation
- Watch the 3D visualization update in real-time with live data

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
├── app.py                       # Main 3D simulation app (START HERE)
├── main.py                      # Legacy CLI interface
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── src/
│   ├── core/
│   │   ├── api_integrations.py # Real API data fetching
│   │   ├── world.py            # NetworkX world state
│   │   ├── marketplace.py      # Multi-carrier auctions
│   │   └── schema.py           # Data models
│   ├── agents/
│   │   └── agents.py           # AI agent behaviors
│   ├── ui/
│   │   ├── dashboard.py        # Legacy dashboard
│   │   └── viz_components.py   # 3D rendering components
│   └── utils/
│       └── event_log.py        # Event logging
├── tests/                       # Test files
└── docs/                        # Documentation
```

## 🎓 Learn More

For detailed technical documentation, see:
- **docs/3D_IMPLEMENTATION_SUMMARY.md** - Technical architecture
- **docs/QUICKSTART_3D.md** - Quick start guide
- **docs/MARKETPLACE_UPDATE.md** - Multi-agent marketplace details

## 📝 License

MIT License - See LICENSE file for details.

---

**Built with**: Python, Streamlit, PyDeck, NetworkX, OpenWeatherMap API
