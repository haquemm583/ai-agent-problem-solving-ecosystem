"""
FastAPI Backend for MA-GET 3D Simulation
Serves real-time logistics data to React frontend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import logging

from src.core.world import WorldState
from src.core.api_integrations import RealDataIntegrator
from src.core.market_heartbeat import MarketHeartbeat, MarketHeartbeatConfig

# =============================================================================
# SETUP
# =============================================================================

app = FastAPI(title="MA-GET Simulation API", version="2.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("MA-GET.API")

# Global state
world = WorldState()
data_integrator = RealDataIntegrator()
heartbeat_config = MarketHeartbeatConfig(
    tick_interval_seconds=2.0,
    auto_generate_orders=True,
    max_orders_per_tick=1
)
heartbeat = MarketHeartbeat(world, heartbeat_config)

# Simulation state
simulation_running = False
tick_count = 0

# =============================================================================
# RESPONSE MODELS
# =============================================================================

class CityData(BaseModel):
    name: str
    latitude: float
    longitude: float
    inventory: int
    capacity: int
    demand_rate: float

class RouteData(BaseModel):
    source: str
    target: str
    distance: float
    weather: str
    fuel_multiplier: float
    is_open: bool

class SimulationState(BaseModel):
    running: bool
    tick_count: int
    total_orders: int
    active_routes: int

class WorldData(BaseModel):
    cities: List[CityData]
    routes: List[RouteData]
    simulation: SimulationState

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "message": "MA-GET Simulation API"}

@app.get("/api/world", response_model=WorldData)
async def get_world_state():
    """Get current world state including cities, routes, and simulation status"""
    global tick_count
    
    # Get cities
    cities = []
    for city in world.get_all_cities():
        cities.append(CityData(
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            inventory=city.current_inventory,
            capacity=city.warehouse_capacity,
            demand_rate=city.demand_rate
        ))
    
    # Get routes
    routes = []
    for route in world.get_all_routes():
        routes.append(RouteData(
            source=route.source,
            target=route.target,
            distance=route.base_distance,
            weather=route.weather_status.value,
            fuel_multiplier=route.fuel_multiplier,
            is_open=route.is_open
        ))
    
    # Get simulation state
    stats = heartbeat.get_statistics()
    simulation = SimulationState(
        running=simulation_running,
        tick_count=tick_count,
        total_orders=stats.get('total_orders_generated', 0),
        active_routes=len([r for r in world.get_all_routes() if r.is_open])
    )
    
    return WorldData(
        cities=cities,
        routes=routes,
        simulation=simulation
    )

@app.post("/api/simulation/start")
async def start_simulation():
    """Start the simulation"""
    global simulation_running
    simulation_running = True
    logger.info("Simulation started")
    return {"status": "started", "running": True}

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the simulation"""
    global simulation_running
    simulation_running = False
    logger.info("Simulation stopped")
    return {"status": "stopped", "running": False}

@app.post("/api/simulation/tick")
async def simulation_tick():
    """Advance simulation by one tick (called by frontend)"""
    global tick_count
    
    if simulation_running:
        # Update with real API data
        data_integrator.update_world_with_real_data(world)
        
        # Advance simulation
        heartbeat.tick()
        tick_count += 1
        
        logger.debug(f"Tick {tick_count}")
    
    return {"tick": tick_count, "running": simulation_running}

@app.get("/api/simulation/status")
async def get_simulation_status():
    """Get current simulation status"""
    return {
        "running": simulation_running,
        "tick_count": tick_count
    }

# =============================================================================
# STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
