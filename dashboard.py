"""
MA-GET Streamlit Dashboard - "God View"
Visualizes the NetworkX graph and live negotiation logs.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import networkx as nx
from datetime import datetime
import time
import uuid
import json
import os
from typing import Dict, List, Optional

# Import from project
from schema import (
    Order, OrderPriority, NegotiationState, NegotiationStatus,
    WeatherStatus, AgentType, MarketplaceAuction
)
from world import WorldState, calculate_fair_price_range, EnvironmentalChaosGenerator
from agents import WarehouseAgent, CarrierAgent, create_negotiation_graph
from marketplace import MarketplaceOrchestrator, create_default_carrier_fleet
from event_log import EventLog, EventType, SimulationEvent
import deal_database as db

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="MA-GET Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 5px;
    }
    .event-card {
        background-color: #2d2d2d;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #4CAF50;
    }
    .event-card.offer { border-left-color: #2196F3; }
    .event-card.response { border-left-color: #FF9800; }
    .event-card.monologue { border-left-color: #9C27B0; }
    .agent-warehouse { color: #4CAF50; }
    .agent-carrier { color: #2196F3; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    if 'world' not in st.session_state:
        st.session_state.world = WorldState()
    
    if 'negotiation_history' not in st.session_state:
        st.session_state.negotiation_history = []
    
    if 'auction_history' not in st.session_state:
        st.session_state.auction_history = []
    
    if 'events' not in st.session_state:
        st.session_state.events = []
    
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    
    if 'chaos_generator' not in st.session_state:
        st.session_state.chaos_generator = EnvironmentalChaosGenerator(
            st.session_state.world, chaos_level=0.3
        )
    
    if 'marketplace_orchestrator' not in st.session_state:
        st.session_state.marketplace_orchestrator = MarketplaceOrchestrator(st.session_state.world)


# =============================================================================
# GRAPH VISUALIZATION
# =============================================================================

def create_network_graph(world: WorldState) -> go.Figure:
    """Create an interactive Plotly visualization of the network graph."""
    
    # Get positions using spring layout
    G = world.graph
    pos = nx.spring_layout(G, seed=42, k=2)
    
    # Use actual Texas coordinates for more realistic layout
    texas_coords = {
        "Corpus Christi": (0.0, -1.0),
        "Houston": (1.0, 0.0),
        "San Antonio": (-0.3, 0.0),
        "Austin": (-0.2, 0.5),
        "Dallas": (0.5, 1.2)
    }
    pos = texas_coords
    
    # Create edge traces
    edge_traces = []
    edge_annotations = []
    
    weather_colors = {
        WeatherStatus.CLEAR: "#4CAF50",
        WeatherStatus.RAIN: "#2196F3",
        WeatherStatus.FOG: "#9E9E9E",
        WeatherStatus.STORM: "#FF9800",
        WeatherStatus.SEVERE: "#F44336"
    }
    
    for edge in G.edges(data=True):
        source, target, data = edge
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        
        weather = data.get('weather_status', WeatherStatus.CLEAR)
        is_open = data.get('is_open', True)
        distance = data.get('base_distance', 0)
        fuel_mult = data.get('fuel_multiplier', 1.0)
        
        color = weather_colors.get(weather, "#4CAF50")
        if not is_open:
            color = "#F44336"
            dash = "dash"
        else:
            dash = "solid"
        
        # Edge line
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=3 if is_open else 1, color=color, dash=dash),
            hoverinfo='text',
            text=f"{source} ↔ {target}<br>Distance: {distance:.0f}mi<br>Fuel: {fuel_mult:.2f}x<br>Weather: {weather.value}",
            showlegend=False
        )
        edge_traces.append(edge_trace)
        
        # Edge label (distance)
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        edge_annotations.append(
            dict(
                x=mid_x, y=mid_y,
                text=f"{distance:.0f}mi",
                showarrow=False,
                font=dict(size=10, color="white"),
                bgcolor="rgba(0,0,0,0.5)",
                borderpad=2
            )
        )
    
    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []
    
    for node in G.nodes(data=True):
        name, data = node
        x, y = pos[name]
        node_x.append(x)
        node_y.append(y)
        
        inventory = data.get('current_inventory', 0)
        capacity = data.get('warehouse_capacity', 1000)
        fill_pct = (inventory / capacity) * 100 if capacity > 0 else 0
        
        node_text.append(
            f"<b>{name}</b><br>"
            f"Inventory: {inventory}/{capacity} ({fill_pct:.0f}%)<br>"
            f"Demand Rate: {data.get('demand_rate', 1.0):.1f}x"
        )
        
        # Color by inventory level
        if fill_pct > 70:
            node_colors.append("#4CAF50")  # Green
        elif fill_pct > 30:
            node_colors.append("#FF9800")  # Orange
        else:
            node_colors.append("#F44336")  # Red
        
        node_sizes.append(30 + (fill_pct / 5))
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[n for n in G.nodes()],
        textposition="top center",
        textfont=dict(size=12, color="white"),
        hovertext=node_text,
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white'),
            symbol='circle'
        ),
        showlegend=False
    )
    
    # Create figure
    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            title=dict(
                text="🌍 Texas Logistics Network",
                font=dict(size=20, color="white")
            ),
            showlegend=False,
            hovermode='closest',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=edge_annotations,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=20, r=20, t=50, b=20),
            height=500
        )
    )
    
    # Add legend for weather
    legend_items = [
        ("☀️ Clear", "#4CAF50"),
        ("🌧️ Rain", "#2196F3"),
        ("🌫️ Fog", "#9E9E9E"),
        ("⛈️ Storm", "#FF9800"),
        ("🌪️ Severe", "#F44336")
    ]
    
    for i, (label, color) in enumerate(legend_items):
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            name=label,
            showlegend=True
        ))
    
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color="white")
        )
    )
    
    return fig


def create_route_status_df(world: WorldState) -> pd.DataFrame:
    """Create a DataFrame of route statuses."""
    routes = world.get_all_routes()
    data = []
    for route in routes:
        weather_icons = {
            WeatherStatus.CLEAR: "☀️",
            WeatherStatus.RAIN: "🌧️",
            WeatherStatus.FOG: "🌫️",
            WeatherStatus.STORM: "⛈️",
            WeatherStatus.SEVERE: "🌪️"
        }
        data.append({
            "Route": f"{route.source} ↔ {route.target}",
            "Distance": f"{route.base_distance:.0f} mi",
            "Fuel": f"{route.fuel_multiplier:.2f}x",
            "Weather": f"{weather_icons.get(route.weather_status, '❓')} {route.weather_status.value}",
            "Status": "✅ Open" if route.is_open else "🚧 Closed"
        })
    return pd.DataFrame(data)


# =============================================================================
# EVENT LOG DISPLAY
# =============================================================================

def display_auction_comparison(auction: MarketplaceAuction):
    """Display bid comparison table for an auction."""
    st.subheader("🎪 Marketplace Bidding War")
    
    if not auction.bids:
        st.info("No bids received for this auction.")
        return
    
    # Create bid comparison table
    bid_data = []
    for bid in auction.bids:
        score = auction.bid_scores.get(bid.sender_id, 0)
        is_winner = bid.sender_id == auction.winner_id
        
        bid_data.append({
            "🏆": "🥇" if is_winner else "",
            "Carrier": bid.sender_id,
            "Price": bid.offer_price,
            "ETA (hrs)": bid.eta_estimate,
            "Score": score,
            "Reasoning": bid.reasoning[:80] + "..." if len(bid.reasoning) > 80 else bid.reasoning
        })
    
    df = pd.DataFrame(bid_data)
    df = df.sort_values("Score", ascending=False)
    
    # Style the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "ETA (hrs)": st.column_config.NumberColumn("ETA", format="%.1f"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1, format="%.3f")
        }
    )
    
    # Visualize bid comparison
    col1, col2 = st.columns(2)
    
    with col1:
        # Price comparison
        fig_price = px.bar(
            df,
            x="Carrier",
            y="Price",
            title="💰 Price Comparison",
            color="Score",
            color_continuous_scale="RdYlGn"
        )
        fig_price.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig_price, use_container_width=True)
    
    with col2:
        # ETA comparison
        fig_eta = px.bar(
            df,
            x="Carrier",
            y="ETA (hrs)",
            title="⏱️ Delivery Time Comparison",
            color="Score",
            color_continuous_scale="RdYlGn"
        )
        fig_eta.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig_eta, use_container_width=True)
    
    # Display selection reasoning
    if auction.selection_reasoning:
        st.info(f"**Why this carrier won:** {auction.selection_reasoning}")


def display_carrier_leaderboard():
    """Display carrier leaderboard with statistics."""
    st.subheader("🏆 Carrier Leaderboard")
    
    # Get carrier statistics from marketplace orchestrator
    if hasattr(st.session_state, 'marketplace_orchestrator'):
        stats = st.session_state.marketplace_orchestrator.get_carrier_statistics()
    else:
        stats = {}
    
    if not stats:
        st.info("No carrier statistics available yet. Run some auctions to see the leaderboard!")
        return
    
    # Create leaderboard data
    leaderboard_data = []
    for carrier_id, data in stats.items():
        # Get carrier persona info from database
        try:
            rep = db.load_reputation_score(carrier_id)
            reputation = rep.overall_score if rep else 0.5
        except:
            reputation = 0.5
        
        leaderboard_data.append({
            "Rank": 0,  # Will be calculated after sorting
            "Carrier": carrier_id,
            "Wins": data["total_wins"],
            "Participations": data["total_participations"],
            "Win %": data["win_percentage"] * 100,
            "Avg Bid": data.get("avg_bid", 0),
            "Total Revenue": data["total_wins"] * data.get("avg_bid", 0),
            "Reputation": reputation
        })
    
    if not leaderboard_data:
        st.info("No carrier data available.")
        return
    
    df = pd.DataFrame(leaderboard_data)
    df = df.sort_values("Wins", ascending=False)
    df["Rank"] = range(1, len(df) + 1)
    
    # Add rank icons
    def get_rank_icon(rank):
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        else:
            return f"{rank}."
    
    df["🏆"] = df["Rank"].apply(get_rank_icon)
    df = df[["🏆", "Carrier", "Wins", "Participations", "Win %", "Avg Bid", "Total Revenue", "Reputation"]]
    
    # Display leaderboard
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Win %": st.column_config.ProgressColumn("Win %", min_value=0, max_value=100, format="%.1f%%"),
            "Avg Bid": st.column_config.NumberColumn("Avg Bid", format="$%.2f"),
            "Total Revenue": st.column_config.NumberColumn("Total Revenue", format="$%.2f"),
            "Reputation": st.column_config.ProgressColumn("Reputation", min_value=0, max_value=1, format="%.2f")
        }
    )
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Win percentage chart
        fig_wins = px.pie(
            df,
            values="Wins",
            names="Carrier",
            title="📊 Market Share (by Wins)",
            hole=0.4
        )
        fig_wins.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig_wins, use_container_width=True)
    
    with col2:
        # Revenue comparison
        fig_revenue = px.bar(
            df,
            x="Carrier",
            y="Total Revenue",
            title="💰 Total Revenue",
            color="Reputation",
            color_continuous_scale="Viridis"
        )
        fig_revenue.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white")
        )
        st.plotly_chart(fig_revenue, use_container_width=True)


def display_events(events: List[SimulationEvent], max_events: int = 50):
    """Display events in a scrollable log."""
    
    if not events:
        st.info("No events yet. Run a negotiation to see activity.")
        return
    
    # Reverse to show newest first
    for event in reversed(events[-max_events:]):
        with st.container():
            # Determine icon and color based on event type
            icons = {
                EventType.SYSTEM: "⚙️",
                EventType.WORLD_UPDATE: "🌍",
                EventType.AGENT_MONOLOGUE: "🧠",
                EventType.OFFER: "💰",
                EventType.RESPONSE: "📨",
                EventType.NEGOTIATION_START: "🤝",
                EventType.NEGOTIATION_END: "✅",
                EventType.WEATHER_CHANGE: "🌦️",
                EventType.ROUTE_UPDATE: "🛣️"
            }
            
            icon = icons.get(event.event_type, "📌")
            time_str = event.timestamp.strftime("%H:%M:%S")
            
            # Agent badge
            agent_badge = ""
            if event.agent_type:
                if event.agent_type == "WAREHOUSE":
                    agent_badge = "🏭"
                elif event.agent_type == "CARRIER":
                    agent_badge = "🚚"
            
            # Create expander for detailed events
            if event.event_type == EventType.AGENT_MONOLOGUE:
                with st.expander(f"{icon} {agent_badge} [{time_str}] {event.title}", expanded=False):
                    if event.data:
                        st.markdown(f"**Context:** {event.data.get('context', '')}")
                        st.markdown(f"**Reasoning:** {event.data.get('reasoning', '')}")
                        st.markdown(f"**Decision:** {event.data.get('decision', '')}")
                        st.progress(event.data.get('confidence', 0.5))
            else:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"{icon} {agent_badge}")
                with col2:
                    st.markdown(f"**[{time_str}]** {event.title}")
                    if event.message:
                        st.caption(event.message)


# =============================================================================
# NEGOTIATION RUNNER
# =============================================================================

def run_negotiation_with_logging(
    order: Order,
    world: WorldState,
    warehouse: WarehouseAgent,
    carrier: CarrierAgent,
    max_rounds: int = 5
) -> NegotiationState:
    """Run negotiation with event logging for dashboard."""
    from event_log import (
        event_log, log_negotiation_start, log_negotiation_end,
        log_offer, log_response, log_agent_monologue
    )
    from schema import GraphState
    
    # Initialize negotiation
    negotiation = NegotiationState(
        negotiation_id=f"NEG-{uuid.uuid4().hex[:8]}",
        order=order,
        warehouse_id=warehouse.agent_id,
        carrier_id=carrier.agent_id,
        max_rounds=max_rounds
    )
    
    # Log start
    log_negotiation_start(
        negotiation.negotiation_id,
        order.order_id,
        order.origin,
        order.destination,
        warehouse.agent_id,
        carrier.agent_id
    )
    
    # Create graph state
    initial_state = GraphState(
        negotiation=negotiation,
        warehouse_state=warehouse.state,
        carrier_state=carrier.state,
        current_speaker=AgentType.WAREHOUSE,
        messages=[]
    )
    
    # Run the negotiation graph
    graph = create_negotiation_graph(warehouse, carrier, world)
    
    final_state = None
    for state in graph.stream(initial_state):
        for node_name, node_state in state.items():
            if isinstance(node_state, dict):
                final_state = node_state
                negotiation_data = node_state.get('negotiation', {})
                
                # Log offers and responses
                if isinstance(negotiation_data, dict):
                    offers = negotiation_data.get('offers', [])
                    responses = negotiation_data.get('responses', [])
                    
                    # Log latest offer if new
                    if offers:
                        latest = offers[-1]
                        if isinstance(latest, dict):
                            log_offer(
                                latest.get('sender_id', ''),
                                latest.get('sender_type', ''),
                                latest.get('offer_price', 0),
                                latest.get('reasoning', ''),
                                latest.get('order_id', '')
                            )
                    
                    # Log latest response if new
                    if responses:
                        latest = responses[-1]
                        if isinstance(latest, dict):
                            log_response(
                                latest.get('responder_id', ''),
                                latest.get('responder_type', ''),
                                latest.get('status', ''),
                                latest.get('counter_price'),
                                latest.get('reasoning', '')
                            )
            else:
                final_state = node_state
    
    # Extract final negotiation state
    if final_state:
        if isinstance(final_state, dict):
            neg_data = final_state.get('negotiation', {})
            if isinstance(neg_data, dict):
                negotiation = NegotiationState(**neg_data)
        else:
            negotiation = final_state.negotiation
    
    negotiation.completed_at = datetime.now()
    
    # Log end
    log_negotiation_end(
        negotiation.negotiation_id,
        negotiation.final_status.value if negotiation.final_status else "UNKNOWN",
        negotiation.agreed_price,
        negotiation.current_round
    )
    
    return negotiation


# =============================================================================
# MAIN DASHBOARD
# =============================================================================

def main():
    """Main dashboard application."""
    init_session_state()
    
    # Header
    st.title("🌍 MA-GET Dashboard")
    st.markdown("**Multi-Agent Generative Economic Twin** - God View")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Control Panel")
        
        st.subheader("📦 New Order")
        
        cities = ["Corpus Christi", "Houston", "Austin", "San Antonio", "Dallas"]
        
        origin = st.selectbox("Origin", cities, index=0)
        destination = st.selectbox("Destination", [c for c in cities if c != origin], index=0)
        
        weight = st.slider("Weight (kg)", 100, 2000, 500, 100)
        priority = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], index=1)
        max_budget = st.number_input("Max Budget ($)", 200, 2000, 750, 50)
        deadline = st.slider("Deadline (hours)", 4, 72, 24, 4)
        max_rounds = st.slider("Max Negotiation Rounds", 1, 10, 5)
        
        st.divider()
        
        # Run negotiation button
        if st.button("🚀 Start Negotiation", type="primary", use_container_width=True):
            with st.spinner("Running negotiation..."):
                # Create order
                order = Order(
                    order_id=f"ORD-{uuid.uuid4().hex[:6].upper()}",
                    origin=origin,
                    destination=destination,
                    weight_kg=float(weight),
                    priority=OrderPriority(priority),
                    max_budget=float(max_budget),
                    deadline_hours=float(deadline)
                )
                
                # Create agents
                warehouse = WarehouseAgent(
                    agent_id="WH-001",
                    location=origin,
                    budget=10000.0
                )
                
                carrier = CarrierAgent(
                    agent_id="CR-001",
                    location=destination,
                    fleet_size=5
                )
                
                # Run negotiation
                result = run_negotiation_with_logging(
                    order,
                    st.session_state.world,
                    warehouse,
                    carrier,
                    max_rounds
                )
                
                st.session_state.negotiation_history.append(result)
                st.session_state.events = EventLog.load_from_file()
                
                st.success("Negotiation complete!")
                st.rerun()
        
        st.divider()
        
        # Chaos controls
        st.subheader("🌪️ Environmental Chaos")
        chaos_level = st.slider("Chaos Level", 0.0, 1.0, 0.3, 0.1)
        
        if st.button("Generate Chaos", use_container_width=True):
            st.session_state.chaos_generator.state.chaos_level = chaos_level
            events = st.session_state.chaos_generator.generate_chaos()
            if events:
                for event in events:
                    st.toast(event)
            st.rerun()
        
        st.divider()
        
        # Clear events
        if st.button("🗑️ Clear Event Log", use_container_width=True):
            from event_log import event_log
            event_log.clear()
            st.session_state.events = []
            st.rerun()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🗺️ Network View", "🎪 Marketplace", "🏆 Leaderboard"])
    
    with tab1:
        # Original network view
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Network graph
            st.subheader("🗺️ Network Map")
            fig = create_network_graph(st.session_state.world)
            st.plotly_chart(fig, use_container_width=True)
        
        # Route status table
        st.subheader("🛣️ Route Status")
        route_df = create_route_status_df(st.session_state.world)
        st.dataframe(route_df, use_container_width=True, hide_index=True)
    
    with col2:
        # City stats
        st.subheader("📊 City Inventory")
        cities = st.session_state.world.get_all_cities()
        for city in cities:
            fill_pct = (city.current_inventory / city.warehouse_capacity) * 100
            st.metric(
                city.name,
                f"{city.current_inventory:,}",
                f"{fill_pct:.0f}% capacity"
            )
            st.progress(fill_pct / 100)
        
        # Latest negotiation result
        if st.session_state.negotiation_history:
            st.subheader("📋 Latest Deal")
            latest = st.session_state.negotiation_history[-1]
            
            status_colors = {
                NegotiationStatus.ACCEPTED: "🟢",
                NegotiationStatus.REJECTED: "🔴",
                NegotiationStatus.EXPIRED: "🟡"
            }
            
            status_icon = status_colors.get(latest.final_status, "⚪")
            st.markdown(f"**Status:** {status_icon} {latest.final_status.value if latest.final_status else 'N/A'}")
            
            if latest.agreed_price:
                st.markdown(f"**Agreed Price:** ${latest.agreed_price:.2f}")
            if latest.agreed_eta:
                st.markdown(f"**ETA:** {latest.agreed_eta:.1f} hours")
            st.markdown(f"**Rounds:** {latest.current_round}")
        
        # Event Log section
        st.divider()
        st.subheader("📜 Live Event Log")
        
        # Reload events from file
        events = EventLog.load_from_file()
        st.session_state.events = events
        
        # Event type filter
        event_filter = st.multiselect(
            "Filter by event type",
            options=[e.value for e in EventType],
            default=[EventType.OFFER.value, EventType.RESPONSE.value, 
                     EventType.NEGOTIATION_START.value, EventType.NEGOTIATION_END.value]
        )
        
        # Filter events
        filtered_events = [
            e for e in events 
            if e.event_type.value in event_filter
        ]
        
        display_events(filtered_events)
        
        # Negotiation history
        if st.session_state.negotiation_history:
            st.divider()
            st.subheader("📈 Negotiation History")
            
            history_data = []
            for neg in st.session_state.negotiation_history:
                history_data.append({
                    "ID": neg.negotiation_id,
                    "Route": f"{neg.order.origin} → {neg.order.destination}",
                    "Status": neg.final_status.value if neg.final_status else "N/A",
                    "Price": f"${neg.agreed_price:.2f}" if neg.agreed_price else "N/A",
                    "Rounds": neg.current_round,
                    "Time": neg.completed_at.strftime("%H:%M:%S") if neg.completed_at else "N/A"
                })
            
            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True, hide_index=True)
            
            # Price trend chart
            if len(history_data) > 1:
                prices = [neg.agreed_price for neg in st.session_state.negotiation_history if neg.agreed_price]
                if prices:
                    fig = px.line(
                        y=prices,
                        title="Agreed Price Trend",
                        labels={"y": "Price ($)", "index": "Negotiation #"}
                    )
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="white")
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Marketplace view
        st.subheader("🎪 Competitive Marketplace")
        
        # Display latest auction if available
        if st.session_state.auction_history:
            latest_auction = st.session_state.auction_history[-1]
            
            st.markdown(f"**Latest Auction:** {latest_auction.auction_id}")
            st.markdown(f"**Order:** {latest_auction.order.order_id} ({latest_auction.order.origin} → {latest_auction.order.destination})")
            
            display_auction_comparison(latest_auction)
        else:
            st.info("No auction data available. Auctions are created when running the marketplace mode in main.py")
            
            # Show instructions
            with st.expander("📖 How to run marketplace auctions"):
                st.code("""
# Run marketplace auction mode
python main.py auction

# Or run programmatically
from marketplace import MarketplaceOrchestrator, create_default_carrier_fleet
from world import WorldState
from agents import WarehouseAgent

world = WorldState()
warehouse = WarehouseAgent("WH-001", "Corpus Christi")
carriers = create_default_carrier_fleet(world)
orchestrator = MarketplaceOrchestrator(world)

auction = orchestrator.run_auction(warehouse, carriers, order)
                """, language="python")
    
    with tab3:
        # Carrier leaderboard
        display_carrier_leaderboard()
    
    # Footer
    st.divider()
    st.caption("MA-GET v1.0 | Multi-Agent Generative Economic Twin for Logistics")


if __name__ == "__main__":
    main()
