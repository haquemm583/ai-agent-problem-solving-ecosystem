"""
MA-GET: 3D Logistics Simulation
Simplified Interface with Real API Data Integration
Single Start/Stop Button Control
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import time
from datetime import datetime

# Import project modules
from src.core.world import WorldState
from src.core.api_integrations import RealDataIntegrator
from src.ui.viz_components import render_3d_map, create_view_state_from_controls
from src.core.market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="3D Logistics Simulation",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Minimal Dark Theme
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #0a0e1a;
    }
    
    /* Hide unnecessary Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Center the button */
    .stButton {
        display: flex;
        justify-content: center;
        margin-top: 20px;
    }
    
    .stButton > button {
        font-size: 24px;
        padding: 20px 60px;
        border-radius: 50px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* Running state - Stop button (red) */
    .stButton > button[kind="primary"] {
        background-color: #ff4444;
        color: white;
        border: 2px solid #ff6666;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #cc0000;
        transform: scale(1.05);
    }
    
    /* Stopped state - Start button (green) */
    .stButton > button[kind="secondary"] {
        background-color: #44ff44;
        color: #0a0e1a;
        border: 2px solid #66ff66;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #00cc00;
        transform: scale(1.05);
    }
    
    /* Status display */
    .status-text {
        text-align: center;
        font-size: 18px;
        color: #ffffff;
        margin-bottom: 10px;
        font-family: monospace;
    }
    
    /* Info panel */
    .info-panel {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
        color: #00e5ff;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def init_state():
    """Initialize session state variables"""
    if 'world' not in st.session_state:
        st.session_state.world = WorldState()
        
    if 'data_integrator' not in st.session_state:
        st.session_state.data_integrator = RealDataIntegrator()
        
    if 'heartbeat' not in st.session_state:
        # Initialize autonomous engine
        config = MarketHeartbeatConfig(
            tick_interval_seconds=2.0,  # Update every 2 seconds
            auto_generate_orders=True,
            max_orders_per_tick=1
        )
        st.session_state.heartbeat = MarketHeartbeat(st.session_state.world, config)

    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
        
    if 'tick_count' not in st.session_state:
        st.session_state.tick_count = 0
        
    # Fixed camera position for Texas view
    if 'cam_lat' not in st.session_state:
        st.session_state.cam_lat = 30.5
    if 'cam_lon' not in st.session_state:
        st.session_state.cam_lon = -97.5
    if 'cam_zoom' not in st.session_state:
        st.session_state.cam_zoom = 5.8
    if 'cam_pitch' not in st.session_state:
        st.session_state.cam_pitch = 50
    if 'cam_bearing' not in st.session_state:
        st.session_state.cam_bearing = 15


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point"""
    init_state()
    
    # Title
    st.markdown("<h1 style='text-align: center; color: #00e5ff; margin-bottom: 5px;'>🌍 3D Logistics Simulation</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; margin-bottom: 30px;'>Real-time logistics network visualization with live API data</p>", unsafe_allow_html=True)
    
    # Status Display
    status_text = "🟢 RUNNING" if st.session_state.simulation_running else "🔴 STOPPED"
    status_color = "#44ff44" if st.session_state.simulation_running else "#ff4444"
    st.markdown(f"<div class='status-text' style='color: {status_color};'>{status_text}</div>", unsafe_allow_html=True)
    
    # Single Start/Stop Button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.session_state.simulation_running:
            if st.button("⏸ STOP", key="stop_btn", type="primary", use_container_width=True):
                st.session_state.simulation_running = False
                st.rerun()
        else:
            if st.button("▶ START", key="start_btn", type="secondary", use_container_width=True):
                st.session_state.simulation_running = True
                st.rerun()
    
    # Info Panel
    stats = st.session_state.heartbeat.get_statistics()
    st.markdown(f"""
    <div class='info-panel'>
        <strong>Simulation Stats</strong><br>
        Ticks: {st.session_state.tick_count} | 
        Orders: {stats.get('total_orders_generated', 0)} | 
        Active Routes: {len([r for r in st.session_state.world.get_all_routes() if r.is_open])}
    </div>
    """, unsafe_allow_html=True)
    
    # Main 3D Visualization
    if st.session_state.simulation_running:
        # Update with real API data every tick
        st.session_state.data_integrator.update_world_with_real_data(st.session_state.world)
        
        # Advance simulation
        st.session_state.heartbeat.tick()
        st.session_state.tick_count += 1
        
        # Small delay to control update rate
        time.sleep(1)
    
    # Render 3D Map
    view_state = create_view_state_from_controls(
        lat=st.session_state.cam_lat,
        lon=st.session_state.cam_lon,
        zoom=st.session_state.cam_zoom,
        pitch=st.session_state.cam_pitch,
        bearing=st.session_state.cam_bearing
    )
    
    deck = render_3d_map(st.session_state.world, view_state)
    st.pydeck_chart(deck, use_container_width=True)
    
    # Auto-rerun if simulation is running
    if st.session_state.simulation_running:
        st.rerun()


if __name__ == "__main__":
    main()
