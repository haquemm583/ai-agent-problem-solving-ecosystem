# MA-GET Competitive Marketplace Update

## Overview
The MA-GET logistics simulation has been evolved from a 1-vs-1 negotiation system into a **Competitive Marketplace** where multiple carriers with different economic profiles compete for shipping orders through a bidding process.

## Architecture Changes

### 1. Carrier Polymorphism (`agents.py`)
Carriers now support distinct "Market Personas" with different operational characteristics:

#### **SwiftLogistics (Premium Carrier)**
- **Profile**: High-end, speed-focused carrier
- **Profit Target**: $3.50/mile
- **Characteristics**:
  - 15% higher pricing
  - 15% faster delivery (0.85x standard ETA)
  - High reputation
  - Premium fleet with better fuel efficiency
  - Speed priority: 1.8x

#### **EcoFreight (Green Carrier)**
- **Profile**: Environmentally-conscious carrier
- **Profit Target**: $2.80/mile
- **Characteristics**:
  - 8% higher pricing
  - 5% slower delivery (1.05x standard ETA)
  - Excellent fuel efficiency
  - 95% green rating
  - Focus on low-carbon routes
  - Speed priority: 0.9x

#### **BudgetTrucking (Discount Carrier)**
- **Profile**: Cost-effective, budget carrier
- **Profit Target**: $1.80/mile
- **Characteristics**:
  - 8% lower pricing
  - 15% slower delivery (1.15x standard ETA)
  - Older fleet with higher fuel costs
  - Lower green rating (30%)
  - Speed priority: 0.7x

### 2. Schema Updates (`schema.py`)

#### New Models:
```python
class CarrierPersona(str, Enum):
    PREMIUM = "PREMIUM"
    GREEN = "GREEN"
    DISCOUNT = "DISCOUNT"

class MarketplaceAuction(BaseModel):
    auction_id: str
    order: Order
    warehouse_id: str
    bids: List[NegotiationOffer]
    participating_carriers: List[str]
    winner_id: Optional[str]
    winning_bid: Optional[NegotiationOffer]
    selection_reasoning: str
    bid_scores: Dict[str, float]
```

#### Enhanced CarrierState:
- Added `persona` field for market identity
- Added `company_name` for branding
- Added `speed_priority` for speed vs. cost tradeoff
- Added `green_rating` for environmental friendliness

### 3. Marketplace Orchestration (`marketplace.py`)

#### MarketplaceOrchestrator Class
Manages the complete auction workflow:

**Key Methods:**
- `run_auction()`: Orchestrates the full bidding process
- `_collect_bids()`: Gathers bids from all carriers in parallel
- `get_carrier_statistics()`: Tracks wins, participation, and revenue
- `get_auction_history()`: Returns completed auction records

**Auction Phases:**
1. **Broadcast Phase**: Order details sent to all carriers
2. **Bidding Phase**: Carriers generate bids based on their personas
3. **Evaluation Phase**: Warehouse evaluates using weighted scoring
4. **Selection Phase**: Winner announced with reasoning

### 4. Warehouse Evaluation Logic (`agents.py`)

#### WarehouseAgent.evaluate_bids()
Implements a sophisticated scoring algorithm:

```
Score = (Price_Weight × Price_Score) + 
        (Time_Weight × Time_Score) + 
        (Reputation_Weight × Reputation_Score)
```

**Default Weights:**
- Price: 50%
- Delivery Time: 30%
- Reputation: 20%

**Normalization:**
- Scores normalized to 0-1 range
- Lower prices get higher scores (inverted)
- Faster delivery gets higher scores (inverted)
- Reputation pulled from historical database

**LLM Decision Reasoning:**
- Generates human-readable explanation
- Explains tradeoffs between carriers
- Justifies selection based on priorities

## Running the Marketplace

### Command Line

#### Auction Mode (Default):
```bash
python main.py auction
```

#### Legacy 1-vs-1 Negotiation Mode:
```bash
python main.py negotiation
```

### Programmatic Usage

```python
from marketplace import MarketplaceOrchestrator, create_default_carrier_fleet
from world import WorldState
from agents import WarehouseAgent
from schema import Order, OrderPriority

# Initialize
world = WorldState()
warehouse = WarehouseAgent("WH-CC-001", "Corpus Christi", budget=10000.0)
carriers = create_default_carrier_fleet(world)

# Create order
order = Order(
    order_id="ORD-001",
    origin="Corpus Christi",
    destination="Dallas",
    weight_kg=500,
    priority=OrderPriority.HIGH,
    max_budget=1200.0,
    deadline_hours=24.0
)

# Run auction
orchestrator = MarketplaceOrchestrator(world)
auction = orchestrator.run_auction(
    warehouse=warehouse,
    carriers=carriers,
    order=order,
    price_weight=0.5,    # 50% weight on price
    time_weight=0.3,     # 30% weight on delivery time
    reputation_weight=0.2 # 20% weight on reputation
)

# Access results
print(f"Winner: {auction.winner_id}")
print(f"Price: ${auction.winning_bid.offer_price:.2f}")
print(f"Reasoning: {auction.selection_reasoning}")
```

## Dashboard Enhancements (`dashboard.py`)

### New Views:

#### 1. **Marketplace Tab** 🎪
- Displays latest auction results
- Shows all bids with comparative scoring
- Visualizes price vs. ETA tradeoffs
- Presents selection reasoning

**Features:**
- Bid comparison table with winner highlighting
- Price comparison bar chart
- ETA comparison bar chart
- Color-coded scoring

#### 2. **Leaderboard Tab** 🏆
Tracks carrier performance across all auctions:

**Metrics:**
- Total wins
- Win percentage
- Average bid price
- Total revenue
- Reputation score

**Visualizations:**
- Market share pie chart (by wins)
- Revenue comparison bar chart
- Reputation-weighted rankings

### Tab Navigation
```
[🗺️ Network View] [🎪 Marketplace] [🏆 Leaderboard]
```

## Event Logging

Auctions are logged to the event system with:
- All bid details
- Evaluation scores
- Winner selection
- Reasoning explanation

Events can be viewed in the dashboard's live event log.

## Carrier Creation

### Default Fleet:
```python
carriers = create_default_carrier_fleet(world)
# Returns: [SwiftLogistics, EcoFreight, BudgetTrucking]
```

### Custom Carrier:
```python
from schema import CarrierPersona

custom_carrier = CarrierAgent(
    agent_id="CR-CUSTOM-001",
    location="Austin",
    fleet_size=7,
    persona=CarrierPersona.GREEN,
    company_name="GreenRide Logistics"
)
```

## Scoring Algorithm Details

### Price Score Calculation:
```python
if max_price > min_price:
    price_score = 1.0 - (bid_price - min_price) / (max_price - min_price)
else:
    price_score = 1.0
```

### Time Score Calculation:
```python
if max_eta > min_eta:
    time_score = 1.0 - (bid_eta - min_eta) / (max_eta - min_eta)
else:
    time_score = 1.0
```

### Reputation Score:
```python
reputation_score = (carrier.overall_score + carrier.reliability_score) / 2.0
```

## Example Output

```
================================================================================
🎪 MARKETPLACE AUCTION: AUC-a1b2c3d4
================================================================================
📦 Order: Corpus Christi → Dallas
💰 Max Budget: $1200.00
⏱️  Priority: HIGH
👥 Carriers: 3 bidders
================================================================================

📢 Phase 1: Broadcasting order to carriers...

  ✓ Bid received from SwiftLogistics (CR-SWIFT-001)
    └─ Price: $1207.50, ETA: 18.7h

  ✓ Bid received from EcoFreight (CR-ECO-001)
    └─ Price: $1134.00, ETA: 23.1h

  ✓ Bid received from BudgetTrucking (CR-BUDGET-001)
    └─ Price: $965.60, ETA: 25.3h

================================================================================
🧮 Phase 2: Warehouse evaluating bids...

================================================================================
🏆 Phase 3: Winner Selection

🏆 WINNER: CR-BUDGET-001
────────────────────────────────────────────────────────────────────────────────
💰 Winning Bid: $965.60
⏱️  ETA: 25.3 hours
📊 Score: 0.847

📋 SELECTION REASONING:
   Selected CR-BUDGET-001 with overall score of 0.847. This carrier offered 
   the most competitive price of $965.60, which is crucial given our 50% 
   price weight. While other carriers offered variations in price/time 
   tradeoffs, this bid provides the best overall value for our current priorities.

================================================================================
```

## Benefits of Marketplace Architecture

1. **Competitive Pricing**: Warehouses get multiple bids, ensuring market rates
2. **Service Diversity**: Different carriers offer speed/cost/sustainability tradeoffs
3. **Transparent Selection**: LLM explains decision-making rationally
4. **Performance Tracking**: Leaderboard creates accountability
5. **Scalability**: Easy to add new carrier personas
6. **Reputation Integration**: Past performance influences future selections

## Future Enhancements

Potential extensions:
- Dynamic carrier pricing based on demand
- Multi-round bidding with counter-offers
- Carrier coalitions for large orders
- Time-based auction windows
- Geographic specialization bonuses
- Service level agreements (SLAs)

## Technical Notes

### Persistence
- Auction results stored in session state
- Carrier statistics maintained across auctions
- Event log captures all auction activity

### Performance
- Bid collection is parallel (not sequential)
- Scoring algorithm is O(n) where n = number of bids
- Minimal database queries through caching

### Extensibility
- Easy to add new persona types
- Configurable scoring weights
- Pluggable evaluation strategies

---

**Version**: 2.0 - Competitive Marketplace  
**Updated**: January 2026  
**Maintainer**: MA-GET Team
