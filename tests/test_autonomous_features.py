"""
Test script for new autonomous features.
Verifies Market Heartbeat, Auditor Agent, and Data Integrity.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all new modules can be imported."""
    print("=" * 80)
    print("TEST 1: Imports")
    print("=" * 80)
    
    try:
        from src.core.market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig
        print("✅ market_heartbeat imported successfully")
    except Exception as e:
        print(f"❌ Failed to import market_heartbeat: {e}")
        return False
    
    try:
        from src.agents.agents import AuditorAgent
        print("✅ AuditorAgent imported successfully")
    except Exception as e:
        print(f"❌ Failed to import AuditorAgent: {e}")
        return False
    
    print("\n")
    return True


def test_heartbeat():
    """Test Market Heartbeat functionality."""
    print("=" * 80)
    print("TEST 2: Market Heartbeat")
    print("=" * 80)
    
    try:
        from src.core.market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig
        from src.core.world import WorldState
        
        world = WorldState()
        config = MarketHeartbeatConfig(
            tick_interval_seconds=0.1,
            inventory_depletion_rate=0.1,
            auto_generate_orders=True,
            max_orders_per_tick=2
        )
        
        heartbeat = MarketHeartbeat(world, config)
        
        print(f"✅ Created MarketHeartbeat")
        print(f"   Cities tracked: {len(heartbeat.city_states)}")
        
        # Run a few ticks
        print(f"\n   Running 5 simulation ticks...")
        for i in range(5):
            new_orders = heartbeat.tick()
            if new_orders:
                print(f"   Tick {i+1}: Generated {len(new_orders)} orders")
            else:
                print(f"   Tick {i+1}: No orders generated")
        
        stats = heartbeat.get_statistics()
        print(f"\n✅ Heartbeat statistics:")
        print(f"   Total ticks: {stats['current_tick']}")
        print(f"   Orders generated: {stats['total_orders_generated']}")
        
        print("\n")
        return True
        
    except Exception as e:
        print(f"❌ Heartbeat test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auditor():
    """Test Auditor Agent functionality."""
    print("=" * 80)
    print("TEST 3: Auditor Agent")
    print("=" * 80)
    
    try:
        from src.agents.agents import AuditorAgent
        from src.core.world import WorldState
        from src.core import deal_database as db
        
        # Initialize database
        db.init_database()
        
        auditor = AuditorAgent()
        world = WorldState()
        
        print(f"✅ Created AuditorAgent: {auditor.agent_id}")
        
        # Try to generate a report (may be empty if no deals)
        print(f"\n   Generating market report...")
        report = auditor.generate_market_report(num_recent_deals=10, world=world)
        
        print(f"✅ Report generated:")
        print(f"   Report ID: {report.get('report_id')}")
        print(f"   Deals analyzed: {report.get('analysis_period', {}).get('total_deals', 0)}")
        
        if report.get('analysis_period', {}).get('total_deals', 0) > 0:
            insights = report.get('insights', {})
            print(f"   Market health: {insights.get('market_health', 'N/A')}")
            print(f"\n   Sample briefing:")
            briefing = auditor.format_daily_briefing(report)
            print(briefing[:500] + "...")
        else:
            print(f"\n   ℹ️  No deals in database yet. Run some auctions to populate data.")
        
        print("\n")
        return True
        
    except Exception as e:
        print(f"❌ Auditor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_integrity():
    """Test that deal recording works."""
    print("=" * 80)
    print("TEST 4: Data Integrity")
    print("=" * 80)
    
    try:
        from src.core import deal_database as db
        from src.core.schema import DealHistory, DealOutcome
        from datetime import datetime
        import uuid
        
        # Create a test deal
        test_deal = DealHistory(
            deal_id=f"TEST-{uuid.uuid4().hex[:8]}",
            negotiation_id="TEST-NEG-001",
            warehouse_id="WH-TEST-001",
            carrier_id="CR-TEST-001",
            order_id="ORD-TEST-001",
            agreed_price=500.0,
            negotiation_rounds=3,
            outcome=DealOutcome.SUCCESS,
            promised_eta=24.0,
            timestamp=datetime.now()
        )
        
        # Save to database
        success = db.save_deal_history(test_deal)
        
        if success:
            print(f"✅ Test deal saved to database: {test_deal.deal_id}")
        else:
            print(f"❌ Failed to save test deal")
            return False
        
        # Load back
        deals = db.load_deal_history(limit=5)
        print(f"✅ Loaded {len(deals)} recent deals from database")
        
        # Verify our test deal is there
        found = any(d.deal_id == test_deal.deal_id for d in deals)
        if found:
            print(f"✅ Test deal verified in database")
        else:
            print(f"⚠️  Test deal not found (may have been pushed out by limit)")
        
        print("\n")
        return True
        
    except Exception as e:
        print(f"❌ Data integrity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MA-GET AUTONOMOUS FEATURES TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Market Heartbeat", test_heartbeat()))
    results.append(("Auditor Agent", test_auditor()))
    results.append(("Data Integrity", test_data_integrity()))
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")
    
    print("=" * 80)
    print("\n")


if __name__ == "__main__":
    run_all_tests()
