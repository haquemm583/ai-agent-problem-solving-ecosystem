# Quick Start Guide - Autonomous Features

## 🚀 New Features Overview

The MA-GET system now includes:

1. **❤️ Market Heartbeat** - Autonomous demand generation and inventory management
2. **🔍 Auditor Agent** - LLM-powered market analysis and transparency
3. **📝 Data Integrity** - Automatic deal recording to database
4. **📊 Enhanced Dashboard** - Market Auditor and Live Inventory tabs

---

## Installation & Setup

### 1. Ensure Dependencies

All required packages are in `requirements.txt`. No new dependencies needed!

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python -c "import deal_database as db; db.init_database()"
```

### 3. Set OpenAI API Key

The Auditor Agent requires an OpenAI API key for LLM analysis:

```bash
# Windows
set OPENAI_API_KEY=your-api-key-here

# Linux/Mac
export OPENAI_API_KEY=your-api-key-here
```

Or add to `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

---

## Usage Examples

### Example 1: Test New Features

Run the test suite to verify everything works:

```bash
python test_autonomous_features.py
```

Expected output:
```
✅ PASS - Imports
✅ PASS - Market Heartbeat
✅ PASS - Auditor Agent
✅ PASS - Data Integrity

4/4 tests passed
🎉 All tests passed! System is ready.
```

---

### Example 2: Run Market Heartbeat Standalone

Test the autonomous demand generation:

```bash
python market_heartbeat.py
```

This will:
- Initialize all cities with inventory
- Run 20 simulation ticks
- Deplete inventory based on demand
- Auto-generate orders when inventory is low
- Display summary statistics

---

### Example 3: Run Marketplace with Auto-Orders

Create a script to connect heartbeat with marketplace:

```python
# autonomous_marketplace.py
from world import WorldState
from agents import WarehouseAgent
from marketplace import MarketplaceOrchestrator, create_default_carrier_fleet
from market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig

# Setup
world = WorldState()
warehouse = WarehouseAgent("WH-CC-001", "Corpus Christi", budget=50000)
carriers = create_default_carrier_fleet(world)
orchestrator = MarketplaceOrchestrator(world)

# Callback to process auto-generated orders
def process_order(order):
    print(f"\n🆕 Processing auto-generated order: {order.order_id}")
    auction = orchestrator.run_auction(warehouse, carriers, order)
    print(f"✅ Winner: {auction.winner_id} at ${auction.winning_bid.offer_price:.2f}")

# Create and run heartbeat
config = MarketHeartbeatConfig(
    tick_interval_seconds=3.0,
    inventory_depletion_rate=0.1,
    auto_generate_orders=True,
    max_orders_per_tick=1
)

heartbeat = MarketHeartbeat(world, config, on_order_generated=process_order)
heartbeat.run(max_ticks=10)  # Run for 10 ticks
```

Run it:
```bash
python autonomous_marketplace.py
```

---

### Example 4: Generate Market Reports

Analyze market trends with the Auditor Agent:

```python
# generate_report.py
from agents import AuditorAgent
from world import WorldState

# Create auditor
auditor = AuditorAgent()
world = WorldState()

# Generate report
report = auditor.generate_market_report(
    num_recent_deals=50,
    world=world
)

# Display formatted briefing
briefing = auditor.format_daily_briefing(report)
print(briefing)

# Access structured data
insights = report['insights']
print(f"\nMarket Health: {insights['market_health']}")
print(f"Dominant Carrier: {insights['dominant_carrier']}")
print(f"Price Trend: {report['statistics']['price_trend']}")
```

First, run some auctions to populate the database:
```bash
python main.py auction
python main.py auction
python main.py auction
```

Then generate the report:
```bash
python generate_report.py
```

---

### Example 5: Use the Enhanced Dashboard

The dashboard now has 5 tabs:

```bash
streamlit run dashboard.py
```

**Tab 4 - Market Auditor 🔍**:
1. Set number of deals to analyze (10-500)
2. Click "Generate Report"
3. View LLM-powered insights
4. Download report as text file

**Tab 5 - Live Inventory 📊**:
1. Click "Simulate Tick" to advance simulation
2. Watch inventory levels change
3. View auto-generated orders
4. Monitor trends over time

---

## Key Concepts

### Market Heartbeat

**What it does**: Simulates autonomous market dynamics
- Cities consume inventory over time
- System detects low inventory
- Automatically generates purchase orders
- Routes orders to marketplace for bidding

**When to use**: When you want continuous, self-regulating simulation

**Configuration**:
```python
MarketHeartbeatConfig(
    tick_interval_seconds=5.0,      # Time between ticks
    inventory_depletion_rate=0.05,  # % of capacity depleted per tick
    auto_generate_orders=True,       # Enable auto-orders
    max_orders_per_tick=2           # Max orders per tick
)
```

---

### Auditor Agent

**What it does**: Provides market transparency and explainability
- Analyzes deal history from database
- Uses LLM (GPT-4o-mini) for insights
- Identifies trends, anomalies, and opportunities
- Generates actionable recommendations

**When to use**: 
- To understand market dynamics
- To detect unfair pricing
- To optimize carrier selection
- For compliance and reporting

**Report Sections**:
1. **Market Overview**: Total deals, value, success rate
2. **Carrier Performance**: Win rates, average bids
3. **Market Insights**: LLM analysis of trends
4. **Recommendations**: Actionable suggestions

---

### Data Integrity

**What it does**: Ensures all deals are saved to database

**How it works**:
- Every successful auction → `DealHistory` record
- Every accepted negotiation → `DealHistory` record
- Automatic reputation updates
- Enables historical analysis

**Database Location**: `deal_history.db` (SQLite)

**Query Example**:
```python
import deal_database as db

# Load recent deals
deals = db.load_deal_history(limit=10)
for deal in deals:
    print(f"{deal.deal_id}: ${deal.agreed_price:.2f}")

# Get agent statistics
stats = db.get_deal_statistics(agent_id="CR-SWIFT-001")
print(f"Total deals: {stats['total_deals']}")
```

---

## Common Workflows

### Workflow 1: Run Autonomous Simulation

1. Start market heartbeat
2. Connect to marketplace orchestrator
3. Let system run continuously
4. Monitor via dashboard
5. Generate audit reports periodically

### Workflow 2: Analyze Market Performance

1. Run several auctions/negotiations
2. Wait for deals to accumulate in database
3. Open dashboard → Market Auditor tab
4. Generate report with LLM analysis
5. Review insights and recommendations
6. Adjust parameters based on findings

### Workflow 3: Monitor Real-Time Inventory

1. Open dashboard → Live Inventory tab
2. Click "Simulate Tick" repeatedly
3. Watch inventory deplete
4. See auto-orders generated at 30% threshold
5. View trend charts
6. Identify cities needing attention

---

## Troubleshooting

### "No deals in database"
**Solution**: Run some auctions first
```bash
python main.py auction
```

### "Heartbeat not generating orders"
**Solution**: Inventory must fall below 30%. Increase depletion rate or run more ticks.

### "LLM error in Auditor"
**Solution**: Check OPENAI_API_KEY environment variable

### "Import error for AuditorAgent"
**Solution**: Ensure agents.py was updated correctly

### "Dashboard tabs not showing"
**Solution**: Update dashboard.py and restart Streamlit

---

## Performance Notes

- **Heartbeat**: Very lightweight, runs efficiently for hours
- **Auditor**: 1 LLM call per report (~1-2 seconds)
- **Dashboard**: Updates on manual refresh (Streamlit limitation)
- **Database**: SQLite handles thousands of deals easily

---

## Next Steps

1. ✅ Test all features with `test_autonomous_features.py`
2. ✅ Run standalone heartbeat to understand behavior
3. ✅ Generate market reports after running auctions
4. ✅ Explore dashboard tabs 4 and 5
5. ✅ Build your own autonomous workflows!

---

## Support

For detailed documentation, see:
- `AUTONOMOUS_FEATURES_UPDATE.md` - Complete feature documentation
- `README.md` - Main project README
- `MARKETPLACE_UPDATE.md` - Marketplace system details
- `REPUTATION_SYSTEM.md` - Reputation tracking details

---

**Happy Simulating! 🎉**
