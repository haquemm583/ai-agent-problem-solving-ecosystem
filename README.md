# MA-GET: Multi-Agent Generative Economic Twin for Logistics

A **Multi-Agent Generative Economic Twin** simulation for autonomous logistics negotiation and real-time supply chain adaptation.

## 🎯 Overview

MA-GET simulates a Texas-based logistics corridor where autonomous AI agents negotiate shipping contracts in real-time. The system models:

- **Warehouse Agents**: Manage inventory and bid for shipping services (minimize costs)
- **Carrier Agents**: Manage truck fleets and negotiate prices (maximize profit)
- **Environmental Agent**: Introduces real-world chaos (weather, fuel prices, route closures)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MA-GET SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Warehouse  │◄──►│   Carrier   │◄──►│   Environmental     │  │
│  │    Agent    │    │    Agent    │    │   Chaos Generator   │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘  │
│         │                  │                      │             │
│         └──────────────────┼──────────────────────┘             │
│                            ▼                                    │
│              ┌─────────────────────────┐                        │
│              │      WORLD STATE        │                        │
│              │   (NetworkX Graph)      │                        │
│              │   - Cities (Nodes)      │                        │
│              │   - Routes (Edges)      │                        │
│              └─────────────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
ai-agent-problem-solving-ecosystem/
├── main.py          # Orchestration & entry point
├── agents.py        # Agent logic, prompts & LangGraph workflow
├── world.py         # NetworkX graph & environment management
├── schema.py        # Pydantic models for structured communication
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Simulation

```bash
python main.py
```

### 3. Watch the Negotiation

The terminal will display:
- 🌍 World state with cities and routes
- 📦 Order details
- 🧠 Agent internal monologues (reasoning)
- 🤝 Negotiation progress
- ✅ Final deal summary

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

## 🤖 Agent Behavior

### Warehouse Agent Strategy
- Starts with conservative offers (30% of fair price range)
- Increases bids based on urgency and remaining rounds
- Maximum bid capped at order budget

### Carrier Agent Strategy
- Calculates minimum acceptable price (fuel costs + 20% margin)
- Targets profit per mile ($2.50/mile default)
- Becomes more flexible in later negotiation rounds

## 📊 Negotiation Protocol

Agents exchange **Pydantic-validated JSON messages**:

```python
{
    "offer_id": "OFF-abc123",
    "offer_price": 525.00,
    "reasoning": "Starting with conservative offer...",
    "eta_estimate": 3.8,
    "status": "PENDING",
    "confidence": 0.75
}
```

## 🔧 Configuration

### Adjust Agent Parameters

In `main.py`:

```python
warehouse = WarehouseAgent(
    agent_id="WH-CC-001",
    location="Corpus Christi",
    budget=10000.0,          # Total budget
    urgency_threshold=0.7    # When to prioritize speed
)

carrier = CarrierAgent(
    agent_id="CR-TX-001",
    location="Houston",
    fleet_size=5,            # Number of trucks
    profit_target=2.5        # Target $/mile profit
)
```

### Modify World Conditions

In `world.py`:

```python
# Update weather
world.update_weather("Houston", "Austin", WeatherStatus.STORM)

# Change fuel prices
world.update_fuel_multiplier("Corpus Christi", "Houston", 1.5)

# Close a route
world.close_route("Dallas", "Houston")
```

## 📈 Phase 1 Features

- ✅ Pydantic schema for structured agent communication
- ✅ NetworkX graph for Texas logistics network
- ✅ LangGraph workflow for negotiation
- ✅ Rich terminal output with agent monologues
- ✅ Fair price calculation based on distance/weight
- ✅ Environmental chaos generator (weather/fuel)

## 🔜 Future Phases

### Phase 2: Multi-Agent Expansion
- Multiple warehouses and carriers
- Competitive bidding
- Fleet routing optimization

### Phase 3: LLM Integration
- Connect to Ollama (Llama 3.2-3B / Phi-3.5)
- Or OpenAI GPT-4o-mini
- Natural language negotiation strategies

### Phase 4: Streamlit Dashboard
- "God View" visualization
- Real-time simulation monitoring
- Interactive parameter tuning

### Phase 5: Persistence & Analytics
- SQLite database for history
- Performance metrics
- A/B testing strategies

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

This is a solo-developer project focused on learning and experimentation.
