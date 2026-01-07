# Reputation System & Deal History

This document describes the reputation tracking and deal history features added to the MA-GET system.

## Overview

The system now tracks agent performance over time and maintains a persistent database of all completed deals. Agents can query past performance to make more informed negotiation decisions.

## Key Components

### 1. ReputationScore (schema.py)

Tracks an agent's reputation based on:
- **Overall Score** (0.0-1.0): Weighted average of success rate, reliability, and negotiation fairness
- **Reliability Score** (0.0-1.0): On-time delivery percentage (primarily for carriers)
- **Negotiation Fairness** (0.0-1.0): Based on average negotiation rounds (fewer = better)
- **Total Deals**: Number of completed negotiations
- **Success/Failure Counts**: Deal outcome statistics

### 2. DealHistory (schema.py)

Records each completed deal with:
- Participating agents (warehouse and carrier)
- Negotiation details (price, rounds, outcome)
- Performance metrics (on-time delivery, actual vs promised ETA)
- Timestamps

### 3. Deal Database (deal_database.py)

SQLite database providing:
- **Persistence**: All deal history and reputation scores saved to disk
- **Querying**: Fast retrieval by agent, outcome, or time period
- **Statistics**: Aggregate metrics for agents or the entire system
- **Rankings**: Top-performing agents by various metrics

## Database Functions

### Saving Data

```python
# Save a deal
db.save_deal_history(deal_history)

# Save/update reputation
db.save_reputation_score(reputation)

# Automatic: Update reputation when recording a deal
db.update_reputation_from_deal(deal_history)
```

### Loading Data

```python
# Get agent's reputation
reputation = db.load_reputation_score(agent_id)

# Get agent's deal history
deals = db.get_agent_deal_history(agent_id, limit=50)

# Load deals with filters
deals = db.load_deal_history(
    agent_id="WAREHOUSE_001",
    outcome_filter=DealOutcome.SUCCESS,
    limit=100
)
```

### Analytics

```python
# Get statistics
stats = db.get_deal_statistics(agent_id="CARRIER_001")
# Returns: total_deals, successful_deals, avg_negotiation_rounds,
#          avg_agreed_price, on_time_deliveries, on_time_percentage

# Get top performers
top_carriers = db.get_top_agents(
    AgentType.CARRIER,
    limit=10,
    metric="reliability_score"
)
```

## Agent Methods

### BaseAgent Methods (available to all agents)

```python
# Get this agent's reputation
reputation = agent.get_reputation()

# Get deal history
history = agent.get_deal_history(limit=50)

# Record a completed deal (auto-updates reputation)
agent.record_deal(deal_history)

# Get partner's reputation
partner_rep = agent.get_partner_reputation(partner_id)

# Get statistics
stats = agent.get_statistics()
```

### WarehouseAgent Methods

```python
# Evaluate a carrier before negotiating
evaluation = warehouse.evaluate_carrier_reputation(carrier_id)
# Returns: reputation_found, overall_score, reliability_score,
#          recommendation (HIGHLY_RECOMMENDED, RECOMMENDED, CAUTION, AVOID),
#          reasoning
```

### CarrierAgent Methods

```python
# Evaluate a warehouse before negotiating
evaluation = carrier.evaluate_warehouse_reputation(warehouse_id)
# Returns: reputation_found, overall_score, negotiation_fairness,
#          recommendation (PREFERRED_CLIENT, GOOD_CLIENT, DIFFICULT_CLIENT, RISKY_CLIENT),
#          reasoning
```

## Usage Example

```python
from agents import WarehouseAgent, CarrierAgent
from schema import DealHistory, DealOutcome
import deal_database as db

# Create agents (automatically loads reputation from DB)
warehouse = WarehouseAgent("WAREHOUSE_001", "Chicago")
carrier = CarrierAgent("CARRIER_001", "New York")

# Check carrier's reputation before negotiating
carrier_eval = warehouse.evaluate_carrier_reputation("CARRIER_001")
print(f"Carrier recommendation: {carrier_eval['recommendation']}")
print(f"Reasoning: {carrier_eval['reasoning']}")

# After negotiation completes, record the deal
deal = DealHistory(
    deal_id="DEAL_001",
    negotiation_id="NEG_001",
    warehouse_id="WAREHOUSE_001",
    carrier_id="CARRIER_001",
    order_id="ORDER_001",
    agreed_price=850.0,
    negotiation_rounds=3,
    outcome=DealOutcome.SUCCESS,
    on_time_delivery=True,
    actual_eta=24.5,
    promised_eta=24.0
)

# This saves the deal AND updates both agents' reputations
warehouse.record_deal(deal)

# Query updated reputation
updated_rep = warehouse.get_reputation()
print(f"Updated reputation score: {updated_rep.overall_score:.2f}")
```

## Reputation Calculation

The overall reputation score is calculated as:
```
overall_score = (success_rate * 0.5) + (reliability_score * 0.3) + (negotiation_fairness * 0.2)
```

Where:
- **Success Rate** = successful_deals / total_deals
- **Reliability Score** = on_time_percentage (for carriers)
- **Negotiation Fairness**:
  - 1.0 if avg_rounds ≤ 3
  - 0.75 if 3 < avg_rounds ≤ 6
  - 0.5 if avg_rounds > 6

## Database Location

The SQLite database is stored as `deal_history.db` in the project root directory.

## Testing

Run the test script to see the reputation system in action:

```bash
python test_reputation.py
```

This will:
1. Create test agents
2. Simulate several deals with different outcomes
3. Display updated reputation scores
4. Show how agents evaluate each other
5. Display deal history and statistics

## Integration with Main System

The reputation system is automatically integrated:
- Agents load their reputation on initialization
- Call `agent.record_deal(deal_history)` after completing negotiations
- Use `agent.evaluate_carrier_reputation()` or `agent.evaluate_warehouse_reputation()` to check partners before negotiating
- The database persists across sessions, maintaining long-term reputation history
