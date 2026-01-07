"""
MA-GET: Multi-Agent Generative Economic Twin for Logistics
Main Orchestration Module

This is the entry point for the negotiation simulation.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from schema import (
    Order, OrderPriority, NegotiationState, NegotiationStatus,
    GraphState, AgentType, WarehouseState, CarrierState, MarketplaceAuction
)
from world import WorldState, calculate_fair_price_range
from agents import WarehouseAgent, CarrierAgent, create_negotiation_graph
from marketplace import MarketplaceOrchestrator, create_default_carrier_fleet


# =============================================================================
# RICH CONSOLE SETUP
# =============================================================================

console = Console()


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with rich formatting."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )


def print_banner():
    """Print the application banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   ███╗   ███╗ █████╗        ██████╗ ███████╗████████╗           ║
    ║   ████╗ ████║██╔══██╗      ██╔════╝ ██╔════╝╚══██╔══╝           ║
    ║   ██╔████╔██║███████║█████╗██║  ███╗█████╗     ██║              ║
    ║   ██║╚██╔╝██║██╔══██║╚════╝██║   ██║██╔══╝     ██║              ║
    ║   ██║ ╚═╝ ██║██║  ██║      ╚██████╔╝███████╗   ██║              ║
    ║   ╚═╝     ╚═╝╚═╝  ╚═╝       ╚═════╝ ╚══════╝   ╚═╝              ║
    ║                                                                  ║
    ║   Multi-Agent Generative Economic Twin for Logistics            ║
    ║   Phase 1: Hello World Negotiation                              ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_world_state(world: WorldState):
    """Display the world state in a formatted table."""
    console.print("\n")
    console.print(Panel("🌍 WORLD STATE: Texas Logistics Corridor", style="bold green"))
    
    # Cities table
    cities_table = Table(title="📍 Cities", box=box.ROUNDED)
    cities_table.add_column("City", style="cyan")
    cities_table.add_column("Inventory", justify="right")
    cities_table.add_column("Capacity", justify="right")
    cities_table.add_column("Demand Rate", justify="right")
    
    for city in world.get_all_cities():
        cities_table.add_row(
            city.name,
            str(city.current_inventory),
            str(city.warehouse_capacity),
            f"{city.demand_rate:.1f}x"
        )
    
    console.print(cities_table)
    
    # Routes table
    routes_table = Table(title="🛣️ Routes", box=box.ROUNDED)
    routes_table.add_column("Route", style="cyan")
    routes_table.add_column("Distance", justify="right")
    routes_table.add_column("Fuel Mult", justify="right")
    routes_table.add_column("Weather", justify="center")
    routes_table.add_column("Status", justify="center")
    
    weather_icons = {
        "CLEAR": "☀️",
        "RAIN": "🌧️",
        "FOG": "🌫️",
        "STORM": "⛈️",
        "SEVERE": "🌪️"
    }
    
    for route in world.get_all_routes():
        status = "✅ Open" if route.is_open else "🚧 Closed"
        weather_icon = weather_icons.get(route.weather_status.value, "❓")
        routes_table.add_row(
            f"{route.source} ↔ {route.target}",
            f"{route.base_distance:.0f} mi",
            f"{route.fuel_multiplier:.2f}x",
            f"{weather_icon} {route.weather_status.value}",
            status
        )
    
    console.print(routes_table)


def print_order(order: Order, world: WorldState):
    """Display order details."""
    console.print("\n")
    console.print(Panel("📦 ORDER DETAILS", style="bold yellow"))
    
    order_table = Table(box=box.ROUNDED)
    order_table.add_column("Property", style="cyan")
    order_table.add_column("Value", style="white")
    
    order_table.add_row("Order ID", order.order_id)
    order_table.add_row("Route", f"{order.origin} → {order.destination}")
    order_table.add_row("Weight", f"{order.weight_kg} kg")
    order_table.add_row("Priority", order.priority.value)
    order_table.add_row("Max Budget", f"${order.max_budget:.2f}")
    order_table.add_row("Deadline", f"{order.deadline_hours} hours")
    
    # Add fair price range
    min_price, max_price = calculate_fair_price_range(
        world, order.origin, order.destination, order.weight_kg
    )
    order_table.add_row("Fair Price Range", f"${min_price:.2f} - ${max_price:.2f}")
    
    # Add distance
    path, distance = world.get_shortest_path(order.origin, order.destination)
    order_table.add_row("Distance", f"{distance:.0f} miles")
    order_table.add_row("Route Path", " → ".join(path))
    
    console.print(order_table)


def print_negotiation_result(negotiation: NegotiationState):
    """Display the final negotiation result."""
    console.print("\n")
    
    if negotiation.final_status == NegotiationStatus.ACCEPTED:
        style = "bold green"
        title = "✅ NEGOTIATION SUCCESSFUL"
    elif negotiation.final_status == NegotiationStatus.REJECTED:
        style = "bold red"
        title = "❌ NEGOTIATION FAILED"
    else:
        style = "bold yellow"
        title = "⏰ NEGOTIATION EXPIRED"
    
    console.print(Panel(title, style=style))
    
    result_table = Table(box=box.ROUNDED)
    result_table.add_column("Metric", style="cyan")
    result_table.add_column("Value", style="white")
    
    result_table.add_row("Final Status", negotiation.final_status.value if negotiation.final_status else "N/A")
    result_table.add_row("Total Rounds", str(negotiation.current_round))
    
    if negotiation.agreed_price:
        result_table.add_row("Agreed Price", f"${negotiation.agreed_price:.2f}")
    if negotiation.agreed_eta:
        result_table.add_row("Agreed ETA", f"{negotiation.agreed_eta:.1f} hours")
    
    result_table.add_row("Offers Made", str(len(negotiation.offers)))
    result_table.add_row("Responses Made", str(len(negotiation.responses)))
    
    console.print(result_table)
    
    # Print negotiation history
    if negotiation.offers or negotiation.responses:
        console.print("\n")
        console.print(Panel("📜 NEGOTIATION HISTORY", style="bold blue"))
        
        history_table = Table(box=box.ROUNDED)
        history_table.add_column("Round", style="dim")
        history_table.add_column("Agent", style="cyan")
        history_table.add_column("Action", style="yellow")
        history_table.add_column("Price", justify="right")
        
        # Interleave offers and responses
        round_num = 1
        for i, offer in enumerate(negotiation.offers):
            history_table.add_row(
                str(round_num),
                "🏭 Warehouse",
                "Offer",
                f"${offer.offer_price:.2f}"
            )
            
            # Find corresponding responses
            for response in negotiation.responses:
                if response.offer_id == offer.offer_id or (i < len(negotiation.responses)):
                    resp = negotiation.responses[i] if i < len(negotiation.responses) else None
                    if resp:
                        agent = "🚚 Carrier" if resp.responder_type == AgentType.CARRIER else "🏭 Warehouse"
                        price = resp.counter_price if resp.counter_price else "-"
                        if isinstance(price, float):
                            price = f"${price:.2f}"
                        history_table.add_row(
                            "",
                            agent,
                            resp.status.value,
                            price
                        )
                    break
            round_num += 1
        
        console.print(history_table)


def run_negotiation(
    order: Order,
    world: WorldState,
    warehouse: WarehouseAgent,
    carrier: CarrierAgent,
    max_rounds: int = 5
) -> NegotiationState:
    """
    Run a complete negotiation between warehouse and carrier.
    """
    console.print("\n")
    console.print(Panel("🤝 STARTING NEGOTIATION", style="bold magenta"))
    
    # Initialize negotiation state
    negotiation = NegotiationState(
        negotiation_id=f"NEG-{uuid.uuid4().hex[:8]}",
        order=order,
        warehouse_id=warehouse.agent_id,
        carrier_id=carrier.agent_id,
        max_rounds=max_rounds
    )
    
    # Create initial graph state
    initial_state = GraphState(
        negotiation=negotiation,
        warehouse_state=warehouse.state,
        carrier_state=carrier.state,
        current_speaker=AgentType.WAREHOUSE,
        messages=[]
    )
    
    # Create and run the negotiation graph
    graph = create_negotiation_graph(warehouse, carrier, world)
    
    console.print(f"\n⏳ Running negotiation (max {max_rounds} rounds)...\n")
    console.print("-" * 70)
    
    # Execute the graph
    final_state = None
    for state in graph.stream(initial_state):
        # The state is a dict with node name as key
        for node_name, node_state in state.items():
            # node_state might be a dict or GraphState depending on LangGraph version
            if isinstance(node_state, dict):
                # Convert dict to access
                messages = node_state.get('messages', [])
                if messages:
                    console.print(f"  💬 {messages[-1]}")
                # Keep track of final state as dict
                final_state = node_state
            else:
                # It's a GraphState object
                final_state = node_state
                if node_state.messages:
                    console.print(f"  💬 {node_state.messages[-1]}")
    
    console.print("-" * 70)
    
    if final_state:
        # Handle both dict and object access
        if isinstance(final_state, dict):
            negotiation = final_state.get('negotiation', negotiation)
            if isinstance(negotiation, dict):
                # Reconstruct NegotiationState from dict
                negotiation = NegotiationState(**negotiation)
            negotiation.completed_at = datetime.now()
            return negotiation
        else:
            final_state.negotiation.completed_at = datetime.now()
            return final_state.negotiation
    
    return negotiation


def print_auction_result(auction: MarketplaceAuction):
    """Display the auction result in formatted output."""
    console.print("\n")
    
    if auction.is_complete and auction.winner_id:
        style = "bold green"
        title = "🏆 AUCTION COMPLETE"
    else:
        style = "bold red"
        title = "❌ AUCTION FAILED"
    
    console.print(Panel(title, style=style))
    
    result_table = Table(box=box.ROUNDED)
    result_table.add_column("Metric", style="cyan")
    result_table.add_column("Value", style="white")
    
    result_table.add_row("Auction ID", auction.auction_id)
    result_table.add_row("Order ID", auction.order.order_id)
    result_table.add_row("Participating Carriers", str(len(auction.participating_carriers)))
    result_table.add_row("Bids Received", str(len(auction.bids)))
    
    if auction.winner_id:
        result_table.add_row("Winner", auction.winner_id)
        result_table.add_row("Winning Price", f"${auction.winning_bid.offer_price:.2f}")
        result_table.add_row("Estimated Delivery", f"{auction.winning_bid.eta_estimate:.1f} hours")
    
    console.print(result_table)
    
    # Print bid comparison
    if auction.bids:
        console.print("\n")
        console.print(Panel("📊 BID COMPARISON", style="bold blue"))
        
        bids_table = Table(box=box.ROUNDED)
        bids_table.add_column("Rank", style="dim")
        bids_table.add_column("Carrier", style="cyan")
        bids_table.add_column("Price", justify="right", style="yellow")
        bids_table.add_column("ETA", justify="right")
        bids_table.add_column("Score", justify="right", style="green")
        
        # Sort by score
        sorted_bids = sorted(
            [(bid, auction.bid_scores.get(bid.sender_id, 0)) for bid in auction.bids],
            key=lambda x: x[1],
            reverse=True
        )
        
        for i, (bid, score) in enumerate(sorted_bids, 1):
            rank_icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            bids_table.add_row(
                rank_icon,
                bid.sender_id,
                f"${bid.offer_price:.2f}",
                f"{bid.eta_estimate:.1f}h",
                f"{score:.3f}"
            )
        
        console.print(bids_table)


def run_marketplace_auction(
    order: Order,
    world: WorldState,
    warehouse: WarehouseAgent,
    carriers: list[CarrierAgent],
    price_weight: float = 0.5,
    time_weight: float = 0.3,
    reputation_weight: float = 0.2
) -> MarketplaceAuction:
    """
    Run a competitive marketplace auction.
    
    Args:
        order: The shipping order
        world: World state
        warehouse: Warehouse agent
        carriers: List of carrier agents
        price_weight: Weight for price evaluation
        time_weight: Weight for time evaluation
        reputation_weight: Weight for reputation evaluation
        
    Returns:
        Completed MarketplaceAuction
    """
    orchestrator = MarketplaceOrchestrator(world)
    
    auction = orchestrator.run_auction(
        warehouse=warehouse,
        carriers=carriers,
        order=order,
        price_weight=price_weight,
        time_weight=time_weight,
        reputation_weight=reputation_weight
    )
    
    return auction


def main():
    """Main entry point for the MA-GET simulation."""
    import sys
    
    # Setup
    setup_logging(logging.WARNING)  # Reduce noise, we have rich output
    print_banner()
    
    # Check for mode selection
    mode = "auction"  # Default to auction mode
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    # Initialize the world
    console.print("\n🌍 Initializing Texas Logistics Corridor...", style="bold")
    world = WorldState()
    print_world_state(world)
    
    # Create agents
    console.print("\n🤖 Spawning Agents...", style="bold")
    
    warehouse = WarehouseAgent(
        agent_id="WH-CC-001",
        location="Corpus Christi",
        budget=10000.0,
        urgency_threshold=0.7
    )
    console.print(f"  🏭 Warehouse Agent: {warehouse.agent_id} @ {warehouse.state.location}")
    
    if mode == "auction":
        # Create multiple carriers with different personas
        console.print("\n  Creating Competitive Carrier Fleet...")
        carriers = create_default_carrier_fleet(world)
        
        for carrier in carriers:
            persona_emoji = {
                "PREMIUM": "⚡",
                "GREEN": "🌱",
                "DISCOUNT": "💰"
            }.get(carrier.state.persona.value if carrier.state.persona else "NONE", "🚚")
            
            console.print(
                f"  {persona_emoji} {carrier.state.company_name}: "
                f"{carrier.agent_id} @ {carrier.state.current_location} "
                f"(Target: ${carrier.state.profit_target_per_mile:.2f}/mi)"
            )
    else:
        # Single carrier for 1-vs-1 negotiation
        carrier = CarrierAgent(
            agent_id="CR-TX-001",
            location="Houston",
            fleet_size=5,
            profit_target=2.5
        )
        console.print(f"  🚚 Carrier Agent: {carrier.agent_id} @ {carrier.state.current_location}")
    
    # Create an order
    order = Order(
        order_id=f"ORD-{uuid.uuid4().hex[:6].upper()}",
        origin="Corpus Christi",
        destination="Houston",
        weight_kg=500.0,
        volume_m3=2.0,
        priority=OrderPriority.MEDIUM,
        max_budget=750.0,
        deadline_hours=24.0
    )
    print_order(order, world)
    
    # Run based on mode
    if mode == "auction":
        console.print("\n🎪 Running Marketplace Auction Mode", style="bold magenta")
        console.print(f"   Evaluation Weights: Price 50%, Time 30%, Reputation 20%\n")
        
        auction_result = run_marketplace_auction(
            order=order,
            world=world,
            warehouse=warehouse,
            carriers=carriers,
            price_weight=0.5,
            time_weight=0.3,
            reputation_weight=0.2
        )
        
        # Display results
        print_auction_result(auction_result)
        
        # Final summary
        console.print("\n")
        if auction_result.is_complete and auction_result.winner_id:
            savings = order.max_budget - (auction_result.winning_bid.offer_price or 0)
            console.print(
                Panel(
                    f"🏆 Winner: {auction_result.winner_id}\n"
                    f"💰 Winning Bid: ${auction_result.winning_bid.offer_price:.2f}\n"
                    f"📊 Warehouse saved ${savings:.2f} from max budget\n"
                    f"📊 Expected delivery in {auction_result.winning_bid.eta_estimate:.1f} hours\n\n"
                    f"📝 Reasoning:\n   {auction_result.selection_reasoning}",
                    title="🎉 AUCTION SUMMARY",
                    style="bold green"
                )
            )
        else:
            console.print(
                Panel(
                    "The auction did not result in a winner.\n"
                    "Consider adjusting order parameters or carrier availability.",
                    title="📋 NEXT STEPS",
                    style="bold yellow"
                )
            )
    else:
        console.print("\n🤝 Running 1-vs-1 Negotiation Mode", style="bold cyan")
        
        # Run the negotiation
        negotiation_result = run_negotiation(
            order=order,
            world=world,
            warehouse=warehouse,
            carrier=carrier,
            max_rounds=5
        )
        
        # Display results
        print_negotiation_result(negotiation_result)
        
        # Final summary
        console.print("\n")
        if negotiation_result.final_status == NegotiationStatus.ACCEPTED:
            savings = order.max_budget - (negotiation_result.agreed_price or 0)
            console.print(
                Panel(
                    f"📊 Warehouse saved ${savings:.2f} from max budget\n"
                    f"📊 Carrier will deliver in {negotiation_result.agreed_eta:.1f} hours",
                    title="💰 DEAL SUMMARY",
                    style="bold green"
                )
            )
        else:
            console.print(
                Panel(
                    "The negotiation did not result in a deal.\n"
                    "Consider adjusting budgets or constraints.",
                    title="📋 NEXT STEPS",
                    style="bold yellow"
                )
            )
    
    console.print("\n✨ MA-GET Simulation Complete!\n", style="bold cyan")
    console.print("💡 TIP: Run 'python dashboard.py' to view the dashboard", style="dim")


if __name__ == "__main__":
    main()
