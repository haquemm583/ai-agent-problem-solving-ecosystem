"""
Test script to demonstrate the reputation and deal history system.
"""

import uuid
from datetime import datetime, timedelta

from schema import (
    DealHistory, DealOutcome, ReputationScore, AgentType,
    Order, OrderPriority
)
import deal_database as db
from agents import WarehouseAgent, CarrierAgent
from world import WorldState


def test_reputation_system():
    """Test the reputation tracking system."""
    
    print("=" * 70)
    print("TESTING REPUTATION & DEAL HISTORY SYSTEM")
    print("=" * 70)
    
    # Create test agents
    warehouse = WarehouseAgent(
        agent_id="WAREHOUSE_TEST_001",
        location="Chicago",
        use_llm=False
    )
    
    carrier = CarrierAgent(
        agent_id="CARRIER_TEST_001",
        location="New York",
        use_llm=False
    )
    
    print(f"\n✅ Created test agents:")
    print(f"   - {warehouse.agent_id}: Reputation = {warehouse.state.reputation.overall_score:.2f}")
    print(f"   - {carrier.agent_id}: Reputation = {carrier.state.reputation.overall_score:.2f}")
    
    # Simulate some deals
    print(f"\n📊 Simulating deal history...")
    
    deals = [
        {
            "outcome": DealOutcome.SUCCESS,
            "on_time": True,
            "rounds": 3,
            "price": 850.0,
            "eta": 24.0
        },
        {
            "outcome": DealOutcome.SUCCESS,
            "on_time": True,
            "rounds": 2,
            "price": 920.0,
            "eta": 26.0
        },
        {
            "outcome": DealOutcome.SUCCESS,
            "on_time": False,
            "rounds": 4,
            "price": 780.0,
            "eta": 30.0
        },
        {
            "outcome": DealOutcome.SUCCESS,
            "on_time": True,
            "rounds": 3,
            "price": 890.0,
            "eta": 25.0
        },
        {
            "outcome": DealOutcome.FAILED,
            "on_time": None,
            "rounds": 5,
            "price": 0.0,
            "eta": 0.0
        },
    ]
    
    for i, deal_data in enumerate(deals):
        deal = DealHistory(
            deal_id=f"DEAL-{uuid.uuid4().hex[:8]}",
            negotiation_id=f"NEG-{uuid.uuid4().hex[:8]}",
            warehouse_id=warehouse.agent_id,
            carrier_id=carrier.agent_id,
            order_id=f"ORDER-{i+1:03d}",
            agreed_price=deal_data["price"],
            negotiation_rounds=deal_data["rounds"],
            outcome=deal_data["outcome"],
            on_time_delivery=deal_data["on_time"],
            actual_eta=deal_data["eta"],
            promised_eta=24.0,
            timestamp=datetime.now() - timedelta(days=10-i),
            completed_at=datetime.now() - timedelta(days=9-i) if deal_data["outcome"] == DealOutcome.SUCCESS else None
        )
        
        # Record the deal (this updates reputation automatically)
        warehouse.record_deal(deal)
        
        print(f"   Deal {i+1}: {deal_data['outcome'].value} - "
              f"{deal_data['rounds']} rounds, "
              f"On-time: {deal_data['on_time']}")
    
    # Check updated reputations
    print(f"\n📈 Updated Reputations:")
    
    warehouse_rep = warehouse.get_reputation()
    print(f"\n   {warehouse.agent_id}:")
    print(f"      Overall Score: {warehouse_rep.overall_score:.3f}")
    print(f"      Total Deals: {warehouse_rep.total_deals}")
    print(f"      Successful: {warehouse_rep.successful_deals}")
    print(f"      Failed: {warehouse_rep.failed_deals}")
    print(f"      Negotiation Fairness: {warehouse_rep.negotiation_fairness:.3f}")
    print(f"      Avg Rounds: {warehouse_rep.avg_negotiation_rounds:.1f}")
    
    carrier_rep = carrier.get_reputation()
    print(f"\n   {carrier.agent_id}:")
    print(f"      Overall Score: {carrier_rep.overall_score:.3f}")
    print(f"      Total Deals: {carrier_rep.total_deals}")
    print(f"      Successful: {carrier_rep.successful_deals}")
    print(f"      Failed: {carrier_rep.failed_deals}")
    print(f"      Reliability Score: {carrier_rep.reliability_score:.3f}")
    print(f"      On-Time %: {carrier_rep.on_time_percentage:.1%}")
    print(f"      Avg Rounds: {carrier_rep.avg_negotiation_rounds:.1f}")
    
    # Test reputation evaluation
    print(f"\n🔍 Reputation Evaluation:")
    
    warehouse_eval = carrier.evaluate_warehouse_reputation(warehouse.agent_id)
    print(f"\n   Carrier's view of Warehouse:")
    print(f"      Recommendation: {warehouse_eval['recommendation']}")
    print(f"      Reasoning: {warehouse_eval['reasoning']}")
    
    carrier_eval = warehouse.evaluate_carrier_reputation(carrier.agent_id)
    print(f"\n   Warehouse's view of Carrier:")
    print(f"      Recommendation: {carrier_eval['recommendation']}")
    print(f"      Reasoning: {carrier_eval['reasoning']}")
    
    # Show deal history
    print(f"\n📜 Recent Deal History:")
    history = warehouse.get_deal_history(limit=3)
    for deal in history:
        print(f"   - {deal.deal_id}: {deal.outcome.value}, "
              f"${deal.agreed_price:.2f}, {deal.negotiation_rounds} rounds")
    
    # Show statistics
    print(f"\n📊 Deal Statistics:")
    stats = warehouse.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n✅ Reputation system test completed!")
    print("=" * 70)


def test_top_agents():
    """Test the top agents ranking system."""
    
    print("\n" + "=" * 70)
    print("TOP AGENTS RANKING")
    print("=" * 70)
    
    print("\n🏆 Top Carriers by Overall Score:")
    top_carriers = db.get_top_agents(AgentType.CARRIER, limit=5, metric="overall_score")
    
    if top_carriers:
        for i, agent in enumerate(top_carriers, 1):
            print(f"   {i}. {agent['agent_id']}: "
                  f"Score={agent['overall_score']:.3f}, "
                  f"Deals={agent['total_deals']}")
    else:
        print("   No carriers found in database yet.")
    
    print("\n🏆 Top Warehouses by Overall Score:")
    top_warehouses = db.get_top_agents(AgentType.WAREHOUSE, limit=5, metric="overall_score")
    
    if top_warehouses:
        for i, agent in enumerate(top_warehouses, 1):
            print(f"   {i}. {agent['agent_id']}: "
                  f"Score={agent['overall_score']:.3f}, "
                  f"Deals={agent['total_deals']}")
    else:
        print("   No warehouses found in database yet.")
    
    print("=" * 70)


if __name__ == "__main__":
    test_reputation_system()
    test_top_agents()
