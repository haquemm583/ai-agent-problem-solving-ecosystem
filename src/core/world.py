"""
World State Management for MA-GET
NetworkX graph-based geography and environment management.
"""

import networkx as nx
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import logging

from src.core.schema import (
    CityNode, RouteEdge, WorldSnapshot, WeatherStatus,
    EnvironmentalState
)


# =============================================================================
# LOGGING SETUP
# =============================================================================

logger = logging.getLogger("MA-GET.World")


# =============================================================================
# TEXAS LOGISTICS CORRIDOR DATA
# =============================================================================

# 5-node Texas logistics network
TEXAS_CITIES: Dict[str, Dict] = {
    "Corpus Christi": {
        "latitude": 27.8006,
        "longitude": -97.3964,
        "warehouse_capacity": 2000,
        "current_inventory": 800,
        "demand_rate": 0.8
    },
    "Houston": {
        "latitude": 29.7604,
        "longitude": -95.3698,
        "warehouse_capacity": 5000,
        "current_inventory": 2000,
        "demand_rate": 1.5
    },
    "Austin": {
        "latitude": 30.2672,
        "longitude": -97.7431,
        "warehouse_capacity": 3000,
        "current_inventory": 1200,
        "demand_rate": 1.2
    },
    "San Antonio": {
        "latitude": 29.4241,
        "longitude": -98.4936,
        "warehouse_capacity": 3500,
        "current_inventory": 1500,
        "demand_rate": 1.1
    },
    "Dallas": {
        "latitude": 32.7767,
        "longitude": -96.7970,
        "warehouse_capacity": 4500,
        "current_inventory": 1800,
        "demand_rate": 1.4
    }
}

# Highway connections (based on actual Texas highways)
TEXAS_ROUTES: List[Dict] = [
    # I-37: Corpus Christi to San Antonio
    {"source": "Corpus Christi", "target": "San Antonio", "base_distance": 143.0},
    # I-10: San Antonio to Houston
    {"source": "San Antonio", "target": "Houston", "base_distance": 197.0},
    # I-35: San Antonio to Austin
    {"source": "San Antonio", "target": "Austin", "base_distance": 80.0},
    # I-35: Austin to Dallas
    {"source": "Austin", "target": "Dallas", "base_distance": 195.0},
    # TX-71/I-10: Austin to Houston
    {"source": "Austin", "target": "Houston", "base_distance": 165.0},
    # I-45: Houston to Dallas
    {"source": "Houston", "target": "Dallas", "base_distance": 239.0},
    # US-181/TX-35: Corpus Christi to Houston (coastal route)
    {"source": "Corpus Christi", "target": "Houston", "base_distance": 210.0},
]


# =============================================================================
# WORLD STATE CLASS
# =============================================================================

class WorldState:
    """
    Manages the NetworkX graph representing the logistics network.
    Provides methods for querying routes, updating conditions, and persistence.
    """
    
    def __init__(self, name: str = "Texas Logistics Corridor"):
        self.name = name
        self.graph = nx.Graph()
        self.current_tick = 0
        self.created_at = datetime.now()
        self._initialize_texas_network()
        logger.info(f"🌍 WorldState '{name}' initialized with {self.graph.number_of_nodes()} cities and {self.graph.number_of_edges()} routes")
    
    def _initialize_texas_network(self) -> None:
        """Initialize the Texas logistics corridor graph."""
        # Add city nodes
        for city_name, attrs in TEXAS_CITIES.items():
            city_node = CityNode(name=city_name, **attrs)
            self.graph.add_node(
                city_name,
                **city_node.model_dump()
            )
        
        # Add route edges
        for route in TEXAS_ROUTES:
            route_edge = RouteEdge(**route)
            self.graph.add_edge(
                route["source"],
                route["target"],
                **route_edge.model_dump()
            )
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_city(self, city_name: str) -> Optional[CityNode]:
        """Get a city node by name."""
        if city_name in self.graph.nodes:
            data = self.graph.nodes[city_name]
            return CityNode(**data)
        return None
    
    def get_route(self, source: str, target: str) -> Optional[RouteEdge]:
        """Get a route edge between two cities."""
        if self.graph.has_edge(source, target):
            data = self.graph.edges[source, target]
            return RouteEdge(**data)
        return None
    
    def get_all_cities(self) -> List[CityNode]:
        """Get all cities in the network."""
        return [CityNode(**self.graph.nodes[n]) for n in self.graph.nodes]
    
    def get_all_routes(self) -> List[RouteEdge]:
        """Get all routes in the network."""
        return [RouteEdge(**self.graph.edges[e]) for e in self.graph.edges]
    
    def get_shortest_path(self, source: str, target: str) -> Tuple[List[str], float]:
        """
        Find the shortest path between two cities.
        Returns (path_cities, total_distance)
        """
        try:
            path = nx.shortest_path(
                self.graph, source, target,
                weight=lambda u, v, d: d['base_distance'] * d['fuel_multiplier']
            )
            
            total_distance = 0.0
            for i in range(len(path) - 1):
                edge_data = self.graph.edges[path[i], path[i+1]]
                total_distance += edge_data['base_distance']
            
            return path, total_distance
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {source} to {target}")
            return [], 0.0
    
    def get_effective_distance(self, source: str, target: str) -> float:
        """
        Get the effective distance considering fuel multiplier and weather.
        """
        route = self.get_route(source, target)
        if not route:
            return float('inf')
        
        # Weather impact multipliers
        weather_multipliers = {
            WeatherStatus.CLEAR: 1.0,
            WeatherStatus.RAIN: 1.2,
            WeatherStatus.FOG: 1.3,
            WeatherStatus.STORM: 1.5,
            WeatherStatus.SEVERE: 2.0
        }
        
        weather_mult = weather_multipliers.get(route.weather_status, 1.0)
        effective = route.base_distance * route.fuel_multiplier * weather_mult * route.congestion_factor
        
        return effective if route.is_open else float('inf')
    
    def estimate_travel_time(self, source: str, target: str, avg_speed_mph: float = 55.0) -> float:
        """
        Estimate travel time in hours considering all factors.
        """
        effective_distance = self.get_effective_distance(source, target)
        if effective_distance == float('inf'):
            return float('inf')
        return effective_distance / avg_speed_mph
    
    # =========================================================================
    # UPDATE METHODS
    # =========================================================================
    
    def update_weather(self, source: str, target: str, weather: WeatherStatus) -> bool:
        """Update weather status for a route."""
        if self.graph.has_edge(source, target):
            self.graph.edges[source, target]['weather_status'] = weather
            logger.info(f"🌦️ Weather updated on {source} ↔ {target}: {weather.value}")
            return True
        return False
    
    def update_fuel_multiplier(self, source: str, target: str, multiplier: float) -> bool:
        """Update fuel cost multiplier for a route."""
        if self.graph.has_edge(source, target):
            multiplier = max(0.5, min(3.0, multiplier))  # Clamp to valid range
            self.graph.edges[source, target]['fuel_multiplier'] = multiplier
            logger.info(f"⛽ Fuel multiplier updated on {source} ↔ {target}: {multiplier:.2f}x")
            return True
        return False
    
    def update_congestion(self, source: str, target: str, factor: float) -> bool:
        """Update congestion factor for a route."""
        if self.graph.has_edge(source, target):
            factor = max(0.5, min(2.0, factor))
            self.graph.edges[source, target]['congestion_factor'] = factor
            logger.info(f"🚗 Congestion updated on {source} ↔ {target}: {factor:.2f}x")
            return True
        return False
    
    def close_route(self, source: str, target: str) -> bool:
        """Close a route (e.g., due to severe weather)."""
        if self.graph.has_edge(source, target):
            self.graph.edges[source, target]['is_open'] = False
            logger.warning(f"🚧 Route CLOSED: {source} ↔ {target}")
            return True
        return False
    
    def open_route(self, source: str, target: str) -> bool:
        """Reopen a closed route."""
        if self.graph.has_edge(source, target):
            self.graph.edges[source, target]['is_open'] = True
            logger.info(f"✅ Route REOPENED: {source} ↔ {target}")
            return True
        return False
    
    def update_inventory(self, city: str, delta: int) -> bool:
        """Update inventory for a city warehouse."""
        if city in self.graph.nodes:
            current = self.graph.nodes[city]['current_inventory']
            capacity = self.graph.nodes[city]['warehouse_capacity']
            new_inventory = max(0, min(capacity, current + delta))
            self.graph.nodes[city]['current_inventory'] = new_inventory
            logger.info(f"📦 Inventory updated in {city}: {current} → {new_inventory}")
            return True
        return False
    
    # =========================================================================
    # TICK / SIMULATION METHODS
    # =========================================================================
    
    def tick(self) -> None:
        """Advance the simulation by one discrete time step."""
        self.current_tick += 1
        logger.debug(f"⏰ World tick: {self.current_tick}")
    
    def get_snapshot(self) -> WorldSnapshot:
        """Get a complete snapshot of the current world state."""
        return WorldSnapshot(
            timestamp=datetime.now(),
            tick=self.current_tick,
            cities=self.get_all_cities(),
            routes=self.get_all_routes()
        )
    
    # =========================================================================
    # DISPLAY METHODS
    # =========================================================================
    
    def print_network_summary(self) -> None:
        """Print a summary of the network to the console."""
        print("\n" + "="*60)
        print(f"🌍 {self.name}")
        print("="*60)
        
        print("\n📍 CITIES:")
        for city in self.get_all_cities():
            print(f"  • {city.name}: Inventory {city.current_inventory}/{city.warehouse_capacity}")
        
        print("\n🛣️ ROUTES:")
        for route in self.get_all_routes():
            status = "✅" if route.is_open else "🚧"
            weather_icon = {
                WeatherStatus.CLEAR: "☀️",
                WeatherStatus.RAIN: "🌧️",
                WeatherStatus.FOG: "🌫️",
                WeatherStatus.STORM: "⛈️",
                WeatherStatus.SEVERE: "🌪️"
            }.get(route.weather_status, "❓")
            
            print(f"  {status} {route.source} ↔ {route.target}: "
                  f"{route.base_distance:.0f}mi | Fuel: {route.fuel_multiplier:.1f}x | "
                  f"Weather: {weather_icon} {route.weather_status.value}")
        
        print("="*60 + "\n")


# =============================================================================
# ENVIRONMENTAL CHAOS GENERATOR
# =============================================================================

class EnvironmentalChaosGenerator:
    """
    Autonomous agent that introduces environmental changes to the world.
    Simulates weather changes, fuel price fluctuations, and route closures.
    """
    
    def __init__(self, world: WorldState, chaos_level: float = 0.2):
        self.world = world
        self.state = EnvironmentalState(
            chaos_level=max(0.0, min(1.0, chaos_level))
        )
        logger.info(f"🌪️ Environmental Chaos Generator initialized (chaos_level: {self.state.chaos_level})")
    
    def generate_chaos(self) -> List[str]:
        """
        Generate random environmental events based on chaos level.
        Returns a list of event descriptions.
        """
        events = []
        
        for edge in self.world.graph.edges:
            source, target = edge
            
            # Weather changes
            if random.random() < self.state.chaos_level * 0.5:
                new_weather = random.choice([
                    WeatherStatus.CLEAR, WeatherStatus.CLEAR,  # Weighted toward clear
                    WeatherStatus.RAIN, WeatherStatus.FOG,
                    WeatherStatus.STORM
                ])
                self.world.update_weather(source, target, new_weather)
                if new_weather != WeatherStatus.CLEAR:
                    events.append(f"Weather change on {source}-{target}: {new_weather.value}")
            
            # Fuel price fluctuations
            if random.random() < self.state.chaos_level * 0.3:
                current_mult = self.world.graph.edges[edge]['fuel_multiplier']
                change = random.uniform(-0.2, 0.3)  # Slight bias toward increase
                new_mult = max(0.5, min(3.0, current_mult + change))
                self.world.update_fuel_multiplier(source, target, new_mult)
                if abs(change) > 0.1:
                    events.append(f"Fuel price {'increase' if change > 0 else 'decrease'} on {source}-{target}")
            
            # Rare: Route closures/reopenings
            if random.random() < self.state.chaos_level * 0.05:
                is_open = self.world.graph.edges[edge]['is_open']
                if is_open:
                    self.world.close_route(source, target)
                    events.append(f"⚠️ ROUTE CLOSED: {source}-{target}")
                else:
                    self.world.open_route(source, target)
                    events.append(f"Route reopened: {source}-{target}")
        
        self.state.current_tick = self.world.current_tick
        self.state.last_update = datetime.now()
        self.state.active_events = events
        
        return events


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_shipping_cost(
    distance: float,
    fuel_multiplier: float = 1.0,
    base_rate_per_mile: float = 2.50,
    weight_kg: float = 100.0
) -> float:
    """
    Calculate estimated shipping cost.
    
    Args:
        distance: Distance in miles
        fuel_multiplier: Current fuel cost multiplier
        base_rate_per_mile: Base cost per mile
        weight_kg: Package weight in kg
        
    Returns:
        Estimated cost in dollars
    """
    # Weight factor: heavier packages cost more
    weight_factor = 1.0 + (weight_kg / 1000.0) * 0.5
    
    return distance * base_rate_per_mile * fuel_multiplier * weight_factor


def calculate_fair_price_range(
    world: WorldState,
    source: str,
    target: str,
    weight_kg: float = 100.0
) -> Tuple[float, float]:
    """
    Calculate a fair price range for shipping between two cities.
    Returns (min_price, max_price)
    """
    route = world.get_route(source, target)
    if not route:
        # Try shortest path
        path, distance = world.get_shortest_path(source, target)
        if not path:
            return (0.0, 0.0)
        # Sum up route costs
        total_distance = distance
        avg_fuel_mult = 1.0
    else:
        total_distance = route.base_distance
        avg_fuel_mult = route.fuel_multiplier
    
    base_cost = calculate_shipping_cost(total_distance, avg_fuel_mult, weight_kg=weight_kg)
    
    # Add margin range
    min_price = base_cost * 0.8   # Carrier's minimum acceptable
    max_price = base_cost * 1.5   # Warehouse's maximum budget
    
    return (min_price, max_price)


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    
    # Create and display world
    world = WorldState()
    world.print_network_summary()
    
    # Test pathfinding
    print("\n🗺️ Testing Pathfinding:")
    path, dist = world.get_shortest_path("Corpus Christi", "Dallas")
    print(f"  Corpus Christi → Dallas: {' → '.join(path)} ({dist:.0f} miles)")
    
    path, dist = world.get_shortest_path("Corpus Christi", "Houston")
    print(f"  Corpus Christi → Houston: {' → '.join(path)} ({dist:.0f} miles)")
    
    # Test price calculation
    print("\n💰 Fair Price Ranges:")
    for (src, tgt) in [("Corpus Christi", "Houston"), ("Austin", "Dallas")]:
        min_p, max_p = calculate_fair_price_range(world, src, tgt)
        print(f"  {src} → {tgt}: ${min_p:.2f} - ${max_p:.2f}")
    
    # Test chaos generator
    print("\n🌪️ Testing Chaos Generator:")
    chaos = EnvironmentalChaosGenerator(world, chaos_level=0.5)
    events = chaos.generate_chaos()
    for event in events:
        print(f"  • {event}")
    
    world.print_network_summary()
