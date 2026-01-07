"""
MA-GET "Mission Control" Dashboard
Single-view, 3D-centric visualization of the autonomous logistics network.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import time
from datetime import datetime

# Import project modules
from world import WorldState, EnvironmentalChaosGenerator
from market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig
from event_log import EventLog, EventType
from viz_components import render_3d_map, create_view_state_from_controls
import deal_database as db

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="MA-GET Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark Mode CSS for "Command Center" vibe
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00e5ff;
        font-family: 'Courier New', monospace;
    }
    div[data-testid="stMetricLabel"] {
        color: #888;
        font-size: 14px;
    }
    
    /* News Feed Card Styling */
    .feed-card {
        background: rgba(255, 255, 255, 0.05);
        border-left: 3px solid #00e5ff;
        margin-bottom: 8px;
        padding: 10px;
        border-radius: 4px;
        font-family: 'Segoe UI', sans-serif;
    }
    .feed-card.negotiation { border-left-color: #ffd700; } /* Gold */
    .feed-card.shipment { border-left-color: #00ff00; }    /* Green */
    .feed-card.chaos { border-left-color: #ff0055; }       /* Red */
    
    .feed-time { font-size: 10px; color: #666; font-family: monospace; }
    .feed-title { font-size: 14px; color: #fff; font-weight: 600; }
    .feed-body { font-size: 12px; color: #ccc; margin-top: 4px; }
    
    /* Hide Streamlit elements we don't need */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def init_state():
    if 'world' not in st.session_state:
        st.session_state.world = WorldState()
        
    if 'heartbeat' not in st.session_state:
        # Initialize autonomous engine
        config = MarketHeartbeatConfig(
            tick_interval_seconds=1.0,  # Fast updates
            auto_generate_orders=True,
            max_orders_per_tick=1
        )
        st.session_state.heartbeat = MarketHeartbeat(st.session_state.world, config)

    if 'simulation_active' not in st.session_state:
        st.session_state.simulation_active = False

    # Camera defaults (Texas Centered)
    if 'cam_lat' not in st.session_state: st.session_state.cam_lat = 30.5
    if 'cam_lon' not in st.session_state: st.session_state.cam_lon = -97.5
    if 'cam_zoom' not in st.session_state: st.session_state.cam_zoom = 5.8
    if 'cam_pitch' not in st.session_state: st.session_state.cam_pitch = 50
    if 'cam_bearing' not in st.session_state: st.session_state.cam_bearing = 15


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_feed_item(event):
    """Render a single event card for the side panel."""
    # Determine style class
    css_class = "feed-card"
    if event.event_type in [EventType.OFFER, EventType.NEGOTIATION_START]:
        css_class += " negotiation"
        icon = "🤝"
    elif event.event_type == EventType.NEGOTIATION_END:
        css_class += " shipment"
        icon = "🚛"
    elif event.event_type in [EventType.WEATHER_CHANGE, EventType.ROUTE_UPDATE]:
        css_class += " chaos"
        icon = "⚠️"
    else:
        icon = "ℹ️"

    # HTML Card
    html = f"""
    <div class="{css_class}">
        <div class="feed-time">{event.timestamp.strftime('%H:%M:%S')}</div>
        <div class="feed-title">{icon} {event.title}</div>
        <div class="feed-body">{event.message}</div>
    </div>
    """
    return html

# =============================================================================
# MAIN UI
# =============================================================================

def main():
    init_state()
    
    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.title("🛠️ System Control")
        
        # Simulation Switch
        sim_active = st.toggle("🔴 LIVE SIMULATION", value=st.session_state.simulation_active)
        
        if sim_active and not st.session_state.simulation_active:
            st.session_state.simulation_active = True
            st.rerun()
        elif not sim_active and st.session_state.simulation_active:
            st.session_state.simulation_active = False
            st.rerun()

        st.divider()
        
        # Camera Controls
        st.caption("CAMERA CONTROL")
        st.session_state.cam_pitch = st.slider("Tilt", 0, 80, 50)
        st.session_state.cam_bearing = st.slider("Rotate", 0, 360, 15)
        st.session_state.cam_zoom = st.slider("Zoom", 4.0, 8.0, 5.8)
        
        st.divider()
        
        # Chaos Trigger
        if st.button("🌪️ Trigger Random Event"):
            chaos = EnvironmentalChaosGenerator(st.session_state.world, chaos_level=0.8)
            chaos.generate_chaos()
            st.toast("Chaos Event Injected!")


    # --- TOP METRICS ROW ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate real-time stats
    stats = st.session_state.heartbeat.get_statistics()
    active_neg = len(stats.get('generated_orders', [])) # Simplified proxy
    
    with col1:
        st.metric("System Status", "ONLINE" if st.session_state.simulation_active else "PAUSED", delta_color="normal")
    with col2:
        st.metric("Active Negotiations", active_neg)
    with col3:
        st.metric("Total Orders", stats.get('total_orders_generated', 0))
    with col4:
        # Mock "Network Health" based on open routes
        open_routes = len([r for r in st.session_state.world.get_all_routes() if r.is_open])
        total_routes = len(st.session_state.world.get_all_routes())
        health = int((open_routes/total_routes)*100) if total_routes > 0 else 100
        st.metric("Network Health", f"{health}%")


    # --- MAIN DISPLAY (SPLIT VIEW) ---
    map_col, feed_col = st.columns([3, 1])

    with map_col:
        # 1. Update Simulation State if Active
        if st.session_state.simulation_active:
            # Advance one tick
            st.session_state.heartbeat.tick()
            time.sleep(1) # Pace the simulation
            
        # 2. Render 3D Map
        view_state = create_view_state_from_controls(
            lat=st.session_state.cam_lat,
            lon=st.session_state.cam_lon,
            zoom=st.session_state.cam_zoom,
            pitch=st.session_state.cam_pitch,
            bearing=st.session_state.cam_bearing
        )
        
        deck = render_3d_map(st.session_state.world, view_state)
        st.pydeck_chart(deck, use_container_width=True)
        
        # Rerun to create animation loop if active
        if st.session_state.simulation_active:
            st.rerun()

    with feed_col:
        st.subheader("📡 Live Intelligence")
        
        # Load recent events
        events = EventLog.load_from_file()
        recent_events = reversed(events[-10:]) # Show last 10
        
        event_html = ""
        for event in recent_events:
            event_html += render_feed_item(event)
            
        # Display feed
        st.markdown(f"""
        <div style="height: 500px; overflow-y: auto; padding-right: 5px;">
            {event_html}
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()