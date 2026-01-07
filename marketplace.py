"""
Marketplace Module for MA-GET
Handles multi-carrier auctions and competitive bidding.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from schema import (
    Order, MarketplaceAuction, NegotiationOffer, NegotiationStatus,
    AgentType
)
from agents import WarehouseAgent, CarrierAgent
from world import WorldState
import deal_database as db

# Import event logging
try:
    from event_log import log_event
    EVENT_LOGGING_ENABLED = True
except ImportError:
    EVENT_LOGGING_ENABLED = False


logger = logging.getLogger("MA-GET.Marketplace")


class MarketplaceOrchestrator:
    """Orchestrates competitive auctions between warehouse and multiple carriers."""
    
    def __init__(self, world: WorldState):
        self.world = world
        self.active_auctions: Dict[str, MarketplaceAuction] = {}
        self.completed_auctions: List[MarketplaceAuction] = []
    
    def run_auction(
        self,
        warehouse: WarehouseAgent,
        carriers: List[CarrierAgent],
        order: Order,
        price_weight: float = 0.5,
        time_weight: float = 0.3,
        reputation_weight: float = 0.2
    ) -> MarketplaceAuction:
        """
        Run a complete auction for an order.
        
        Args:
            warehouse: Warehouse agent hosting the auction
            carriers: List of carrier agents to bid
            order: The order to be auctioned
            price_weight: Weight for price in evaluation
            time_weight: Weight for delivery time in evaluation
            reputation_weight: Weight for reputation in evaluation
            
        Returns:
            Completed MarketplaceAuction with winner selected
        """
        auction_id = f"AUC-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🎪 Starting Auction {auction_id} for Order {order.order_id}")
        print(f"\n{'='*80}")
        print(f"🎪 MARKETPLACE AUCTION: {auction_id}")
        print(f"{'='*80}")
        print(f"📦 Order: {order.origin} → {order.destination}")
        print(f"💰 Max Budget: ${order.max_budget:.2f}")
        print(f"⏱️  Priority: {order.priority.value}")
        print(f"👥 Carriers: {len(carriers)} bidders")
        print(f"{'='*80}\n")
        
        # Create auction
        auction = MarketplaceAuction(
            auction_id=auction_id,
            order=order,
            warehouse_id=warehouse.agent_id,
            participating_carriers=[c.agent_id for c in carriers]
        )
        
        self.active_auctions[auction_id] = auction
        
        # Phase 1: Broadcast order and collect bids
        print("📢 Phase 1: Broadcasting order to carriers...\n")
        bids = self._collect_bids(carriers, order, auction_id)
        auction.bids = bids
        
        if not bids:
            logger.warning(f"No bids received for auction {auction_id}")
            auction.is_complete = True
            auction.completed_at = datetime.now()
            return auction
        
        # Log bids
        self._log_bids(bids)
        
        # Phase 2: Warehouse evaluates bids
        print(f"\n{'='*80}")
        print("🧮 Phase 2: Warehouse evaluating bids...\n")
        
        evaluation = warehouse.evaluate_bids(
            bids=bids,
            order=order,
            world=self.world,
            price_weight=price_weight,
            time_weight=time_weight,
            reputation_weight=reputation_weight
        )
        
        # Phase 3: Announce winner
        print(f"{'='*80}")
        print("🏆 Phase 3: Winner Selection\n")
        
        winner_id = evaluation["winner_id"]
        winning_bid = evaluation["winning_bid"]
        auction.winner_id = winner_id
        auction.winning_bid = winning_bid
        auction.bid_scores = evaluation["scores"]
        auction.selection_reasoning = evaluation["reasoning"]
        auction.is_complete = True
        auction.completed_at = datetime.now()
        
        # Print results
        self._print_auction_results(auction, evaluation)
        
        # Log to event system
        if EVENT_LOGGING_ENABLED:
            self._log_auction_event(auction)
        
        # Move to completed
        self.completed_auctions.append(auction)
        del self.active_auctions[auction_id]
        
        logger.info(f"✅ Auction {auction_id} completed. Winner: {winner_id}")
        
        return auction
    
    def _collect_bids(
        self,
        carriers: List[CarrierAgent],
        order: Order,
        auction_id: str
    ) -> List[NegotiationOffer]:
        """Collect bids from all carriers in parallel."""
        bids = []
        
        for carrier in carriers:
            try:
                bid = carrier.create_initial_bid(order, self.world, auction_id)
                bid.recipient_id = order.origin  # Set warehouse location as recipient
                bids.append(bid)
                
                print(f"  ✓ Bid received from {carrier.state.company_name} ({carrier.agent_id})")
                print(f"    └─ Price: ${bid.offer_price:.2f}, ETA: {bid.eta_estimate:.1f}h\n")
                
            except Exception as e:
                logger.error(f"Failed to get bid from {carrier.agent_id}: {e}")
                print(f"  ✗ Failed to get bid from {carrier.agent_id}: {e}\n")
        
        return bids
    
    def _log_bids(self, bids: List[NegotiationOffer]):
        """Log all bids for visibility."""
        print(f"\n{'─'*80}")
        print("📊 BID SUMMARY")
        print(f"{'─'*80}")
        
        # Sort bids by price
        sorted_bids = sorted(bids, key=lambda b: b.offer_price)
        
        for i, bid in enumerate(sorted_bids, 1):
            print(f"{i}. {bid.sender_id}")
            print(f"   💵 Price: ${bid.offer_price:.2f}")
            print(f"   ⏱️  ETA:   {bid.eta_estimate:.1f} hours")
            print(f"   📝 Note:  {bid.reasoning[:100]}...")
            print()
    
    def _print_auction_results(
        self,
        auction: MarketplaceAuction,
        evaluation: Dict[str, Any]
    ):
        """Print formatted auction results."""
        winner_id = auction.winner_id
        winning_bid = auction.winning_bid
        scores = auction.bid_scores
        
        print(f"🏆 WINNER: {winner_id}")
        print(f"{'─'*80}")
        print(f"💰 Winning Bid: ${winning_bid.offer_price:.2f}")
        print(f"⏱️  ETA: {winning_bid.eta_estimate:.1f} hours")
        print(f"📊 Score: {scores[winner_id]:.3f}")
        print(f"\n📋 SELECTION REASONING:")
        print(f"   {auction.selection_reasoning}")
        print(f"\n{'='*80}")
        
        # Show all scores
        print("\n📈 ALL BID SCORES:")
        sorted_carriers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (carrier_id, score) in enumerate(sorted_carriers, 1):
            symbol = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            bid = next(b for b in auction.bids if b.sender_id == carrier_id)
            print(f"{symbol} {rank}. {carrier_id}: {score:.3f} (${bid.offer_price:.2f}, {bid.eta_estimate:.1f}h)")
        
        print(f"{'='*80}\n")
    
    def _log_auction_event(self, auction: MarketplaceAuction):
        """Log auction to event system for dashboard."""
        try:
            event_data = {
                "auction_id": auction.auction_id,
                "order_id": auction.order.order_id,
                "warehouse_id": auction.warehouse_id,
                "num_bids": len(auction.bids),
                "winner_id": auction.winner_id,
                "winning_price": auction.winning_bid.offer_price if auction.winning_bid else None,
                "winning_eta": auction.winning_bid.eta_estimate if auction.winning_bid else None,
                "reasoning": auction.selection_reasoning,
                "bid_scores": auction.bid_scores
            }
            
            log_event(
                event_type="AUCTION_COMPLETE",
                agent_id=auction.warehouse_id,
                agent_type="WAREHOUSE",
                data=event_data
            )
        except Exception as e:
            logger.warning(f"Failed to log auction event: {e}")
    
    def get_auction_history(self, limit: int = 10) -> List[MarketplaceAuction]:
        """Get recent completed auctions."""
        return self.completed_auctions[-limit:]
    
    def get_carrier_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all carriers across completed auctions."""
        stats = {}
        
        for auction in self.completed_auctions:
            # Count participation
            for carrier_id in auction.participating_carriers:
                if carrier_id not in stats:
                    stats[carrier_id] = {
                        "total_participations": 0,
                        "total_wins": 0,
                        "total_bid_value": 0.0,
                        "win_percentage": 0.0
                    }
                
                stats[carrier_id]["total_participations"] += 1
                
                # Find this carrier's bid
                carrier_bid = next((b for b in auction.bids if b.sender_id == carrier_id), None)
                if carrier_bid:
                    stats[carrier_id]["total_bid_value"] += carrier_bid.offer_price
                
                # Check if winner
                if auction.winner_id == carrier_id:
                    stats[carrier_id]["total_wins"] += 1
        
        # Calculate percentages
        for carrier_id, data in stats.items():
            if data["total_participations"] > 0:
                data["win_percentage"] = data["total_wins"] / data["total_participations"]
                data["avg_bid"] = data["total_bid_value"] / data["total_participations"]
        
        return stats


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_default_carrier_fleet(world: WorldState) -> List[CarrierAgent]:
    """
    Create the default fleet of three carriers with different personas.
    
    Returns:
        List of CarrierAgent instances with different market personas
    """
    from schema import CarrierPersona
    
    carriers = [
        CarrierAgent(
            agent_id="CR-SWIFT-001",
            location="Houston",
            fleet_size=8,
            persona=CarrierPersona.PREMIUM,
            company_name="SwiftLogistics"
        ),
        CarrierAgent(
            agent_id="CR-ECO-001",
            location="Dallas",
            fleet_size=6,
            persona=CarrierPersona.GREEN,
            company_name="EcoFreight"
        ),
        CarrierAgent(
            agent_id="CR-BUDGET-001",
            location="San Antonio",
            fleet_size=10,
            persona=CarrierPersona.DISCOUNT,
            company_name="BudgetTrucking"
        )
    ]
    
    return carriers


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    from world import WorldState
    from schema import OrderPriority
    
    # Create world
    world = WorldState()
    
    # Create warehouse
    warehouse = WarehouseAgent(
        agent_id="WH-CC-001",
        location="Corpus Christi",
        budget=5000.0
    )
    
    # Create carrier fleet
    carriers = create_default_carrier_fleet(world)
    
    # Create test order
    order = Order(
        order_id="ORD-TEST-001",
        origin="Corpus Christi",
        destination="Dallas",
        weight_kg=500,
        priority=OrderPriority.HIGH,
        max_budget=1200.0,
        deadline_hours=24.0
    )
    
    # Run auction
    print("\n🧪 Testing Marketplace Auction System\n")
    orchestrator = MarketplaceOrchestrator(world)
    auction = orchestrator.run_auction(
        warehouse=warehouse,
        carriers=carriers,
        order=order,
        price_weight=0.4,
        time_weight=0.4,
        reputation_weight=0.2
    )
    
    print("\n✅ Test completed!")
    print(f"Winner: {auction.winner_id}")
    print(f"Price: ${auction.winning_bid.offer_price:.2f}")
