"""
3D Visualization Components for MA-GET Dashboard
PyDeck-powered Mission Control view with dynamic layers.
"""

import pydeck as pdk
import pandas as pd
from typing import Dict, List, Tuple
from src.core.schema import WeatherStatus, CityNode, RouteEdge
from src.core.world import WorldState


# =============================================================================
# COLOR MAPPINGS
# =============================================================================

def get_inventory_color(current: int, capacity: int) -> List[int]:
    """
    Calculate RGB color for inventory level.
    Green (low usage) to Red (near capacity).
    """
    if capacity == 0:
        return [128, 128, 128, 200]  # Gray for zero capacity
    
    usage_pct = current / capacity
    
    if usage_pct < 0.3:
        # Green (low usage)
        return [0, 255, 0, 200]
    elif usage_pct < 0.7:
        # Yellow-Orange (medium usage)
        r = int(255 * (usage_pct - 0.3) / 0.4)
        g = 255
        return [r, g, 0, 200]
    else:
        # Orange to Red (high usage)
        g = int(255 * (1 - (usage_pct - 0.7) / 0.3))
        return [255, g, 0, 200]


def get_route_width(fuel_multiplier: float) -> float:
    """
    Calculate arc width based on fuel multiplier.
    Thicker = more expensive routes.
    """
    return max(2, min(20, fuel_multiplier * 5))


# =============================================================================
# LAYER BUILDERS
# =============================================================================

def build_inventory_layer(world: WorldState) -> pdk.Layer:
    """
    Layer 1: ColumnLayer for city inventory visualization.
    Elevation represents current inventory level.
    Color represents capacity utilization (green = low, red = high).
    """
    cities_data = []
    
    for city_name in world.graph.nodes():
        city_data = world.graph.nodes[city_name]
        
        # Extract city information
        lat = city_data.get('latitude', 0)
        lon = city_data.get('longitude', 0)
        current_inv = city_data.get('current_inventory', 0)
        capacity = city_data.get('warehouse_capacity', 1000)
        
        # Calculate color based on capacity utilization
        color = get_inventory_color(current_inv, capacity)
        
        cities_data.append({
            'name': city_name,
            'coordinates': [lon, lat],
            'inventory': current_inv,
            'capacity': capacity,
            'elevation': current_inv * 100,  # Scale for visual effect
            'fill_color': color
        })
    
    return pdk.Layer(
        "ColumnLayer",
        data=cities_data,
        get_position='coordinates',
        get_elevation='elevation',
        get_fill_color='fill_color',
        elevation_scale=50,
        radius=20000,
        pickable=True,
        auto_highlight=True,
        extruded=True,
    )


def build_routes_layer(world: WorldState) -> pdk.Layer:
    """
    Layer 2: ArcLayer for highway routes.
    Arc thickness represents fuel multiplier (cost).
    Color gradient: Green (origin) to Red (destination).
    """
    routes_data = []
    
    for edge in world.graph.edges(data=True):
        source, target, edge_data = edge
        
        # Get source and target coordinates
        source_lat = world.graph.nodes[source].get('latitude', 0)
        source_lon = world.graph.nodes[source].get('longitude', 0)
        target_lat = world.graph.nodes[target].get('latitude', 0)
        target_lon = world.graph.nodes[target].get('longitude', 0)
        
        # Get route properties
        fuel_mult = edge_data.get('fuel_multiplier', 1.0)
        distance = edge_data.get('base_distance', 0)
        weather = edge_data.get('weather_status', WeatherStatus.CLEAR)
        is_open = edge_data.get('is_open', True)
        
        # Skip closed routes or make them different
        if not is_open:
            continue
        
        routes_data.append({
            'source': [source_lon, source_lat],
            'target': [target_lon, target_lat],
            'source_name': source,
            'target_name': target,
            'width': get_route_width(fuel_mult),
            'fuel_multiplier': fuel_mult,
            'distance': distance,
            'weather': weather.value,
            'source_color': [0, 255, 0],  # Green at origin
            'target_color': [255, 0, 0],  # Red at destination
        })
    
    return pdk.Layer(
        "ArcLayer",
        data=routes_data,
        get_source_position='source',
        get_target_position='target',
        get_source_color='source_color',
        get_target_color='target_color',
        get_width='width',
        pickable=True,
        auto_highlight=True,
    )


def build_shipments_layer(world: WorldState) -> pdk.Layer:
    """
    Layer 3: ScatterplotLayer for active shipments.
    Shows trucks currently IN_TRANSIT.
    """
    # For now, we'll place markers at cities with active demand
    # In a full implementation, this would track actual shipment positions
    shipments_data = []
    
    for city_name in world.graph.nodes():
        city_data = world.graph.nodes[city_name]
        
        lat = city_data.get('latitude', 0)
        lon = city_data.get('longitude', 0)
        demand = city_data.get('demand_rate', 1.0)
        
        # Simulate active shipments based on demand
        if demand > 1.0:
            shipments_data.append({
                'coordinates': [lon, lat],
                'city': city_name,
                'demand': demand,
                'color': [255, 255, 0, 200],  # Yellow for shipments
                'radius': 15000
            })
    
    return pdk.Layer(
        "ScatterplotLayer",
        data=shipments_data,
        get_position='coordinates',
        get_fill_color='color',
        get_radius='radius',
        pickable=True,
        auto_highlight=True,
    )


# =============================================================================
# MAIN RENDERER
# =============================================================================

def render_3d_map(world_state: WorldState, view_state: Dict = None) -> pdk.Deck:
    """
    Create a 3D Mission Control PyDeck visualization.
    
    Args:
        world_state: Current WorldState with cities, routes, and shipments
        view_state: Optional custom view state (camera position)
    
    Returns:
        pdk.Deck object ready for st.pydeck_chart()
    """
    
    # Build all three layers
    inventory_layer = build_inventory_layer(world_state)
    routes_layer = build_routes_layer(world_state)
    shipments_layer = build_shipments_layer(world_state)
    
    # Default view state (centered on Texas)
    if view_state is None:
        view_state = pdk.ViewState(
            latitude=29.5,
            longitude=-96.5,
            zoom=5.5,
            pitch=45,
            bearing=0,
        )
    
    # Create the deck
    deck = pdk.Deck(
        layers=[routes_layer, inventory_layer, shipments_layer],
        initial_view_state=view_state,
        tooltip={
            "html": """
            <b>{name}</b><br/>
            Inventory: {inventory}/{capacity}<br/>
            <i>{source_name} → {target_name}</i><br/>
            Distance: {distance} mi<br/>
            Fuel Cost: {fuel_multiplier}x<br/>
            Weather: {weather}
            """,
            "style": {
                "backgroundColor": "steelblue",
                "color": "white",
                "fontSize": "12px",
                "padding": "10px"
            }
        },
        map_style="mapbox://styles/mapbox/dark-v10",
    )
    
    return deck


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_view_state_from_controls(lat: float, lon: float, zoom: float, 
                                    pitch: float, bearing: float) -> pdk.ViewState:
    """
    Create a ViewState object from camera controls.
    Used for interactive camera manipulation.
    """
    return pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=zoom,
        pitch=pitch,
        bearing=bearing,
    )


def get_default_texas_view() -> pdk.ViewState:
    """
    Get the default view state centered on Texas logistics corridor.
    """
    return pdk.ViewState(
        latitude=29.5,
        longitude=-96.5,
        zoom=5.5,
        pitch=45,
        bearing=0,
    )
