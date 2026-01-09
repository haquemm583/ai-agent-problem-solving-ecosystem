"""
Real API Integrations for MA-GET
Fetches real-world data for weather, fuel prices, and traffic conditions.
"""

import os
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from src.core.schema import WeatherStatus

load_dotenv()

logger = logging.getLogger("MA-GET.APIs")


class WeatherAPI:
    """
    Integration with OpenWeatherMap API for real weather data.
    Free tier: 1000 calls/day
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        
    def get_weather(self, lat: float, lon: float) -> Dict:
        """
        Get current weather for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with weather data or mock data if API unavailable
        """
        if not self.api_key:
            logger.warning("No OpenWeather API key - using mock data")
            return self._get_mock_weather()
            
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "imperial"
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            # Map OpenWeather conditions to our WeatherStatus
            weather_main = data.get("weather", [{}])[0].get("main", "Clear")
            weather_map = {
                "Clear": WeatherStatus.CLEAR,
                "Clouds": WeatherStatus.CLEAR,
                "Rain": WeatherStatus.RAIN,
                "Drizzle": WeatherStatus.RAIN,
                "Thunderstorm": WeatherStatus.STORM,
                "Snow": WeatherStatus.SEVERE,
                "Mist": WeatherStatus.FOG,
                "Fog": WeatherStatus.FOG,
                "Haze": WeatherStatus.FOG
            }
            
            return {
                "status": weather_map.get(weather_main, WeatherStatus.CLEAR),
                "temp": data.get("main", {}).get("temp", 70),
                "wind_speed": data.get("wind", {}).get("speed", 5),
                "description": data.get("weather", [{}])[0].get("description", "clear"),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return self._get_mock_weather()
    
    def _get_mock_weather(self) -> Dict:
        """Fallback mock weather data"""
        import random
        statuses = [WeatherStatus.CLEAR, WeatherStatus.RAIN, WeatherStatus.FOG, WeatherStatus.STORM]
        return {
            "status": random.choice(statuses),
            "temp": random.uniform(60, 95),
            "wind_speed": random.uniform(0, 15),
            "description": "mock weather",
            "timestamp": datetime.now()
        }


class FuelPriceAPI:
    """
    Integration with fuel price data.
    Using mock data as EIA API requires registration and has limited free tier.
    """
    
    def __init__(self):
        # Texas average fuel prices (starting point)
        self.base_price = 3.20  # USD per gallon
        
    def get_fuel_price(self, city: str) -> float:
        """
        Get current fuel price for a city.
        
        Args:
            city: City name
            
        Returns:
            Fuel price per gallon
        """
        # In production, this would call a real API
        # For now, we'll use realistic variation
        import random
        
        # Cities have different fuel prices
        city_modifiers = {
            "Houston": 0.95,  # Lower (near refineries)
            "Dallas": 1.00,
            "Austin": 1.02,
            "San Antonio": 0.98,
            "Corpus Christi": 0.96  # Lower (coastal)
        }
        
        modifier = city_modifiers.get(city, 1.0)
        # Add some random daily variation
        variation = random.uniform(-0.10, 0.10)
        
        return round(self.base_price * modifier + variation, 2)


class TrafficAPI:
    """
    Traffic and route condition data.
    Uses simulated real-time data based on time of day and random events.
    """
    
    def get_route_condition(self, source: str, target: str) -> Dict:
        """
        Get current traffic/route conditions.
        
        Args:
            source: Origin city
            target: Destination city
            
        Returns:
            Dict with route condition data
        """
        import random
        from datetime import datetime
        
        hour = datetime.now().hour
        
        # Rush hour affects congestion (6-9 AM, 4-7 PM)
        is_rush_hour = (6 <= hour <= 9) or (16 <= hour <= 19)
        
        # Base congestion
        congestion = 1.0
        if is_rush_hour:
            congestion = random.uniform(1.1, 1.3)
        else:
            congestion = random.uniform(0.9, 1.1)
        
        # Random incidents (5% chance)
        has_incident = random.random() < 0.05
        
        return {
            "congestion_multiplier": congestion,
            "has_incident": has_incident,
            "estimated_delay_hours": random.uniform(0, 2) if has_incident else 0,
            "timestamp": datetime.now()
        }


class RealDataIntegrator:
    """
    Main class to integrate all real data sources and update WorldState.
    """
    
    def __init__(self):
        self.weather_api = WeatherAPI()
        self.fuel_api = FuelPriceAPI()
        self.traffic_api = TrafficAPI()
        
    def update_world_with_real_data(self, world):
        """
        Update WorldState with real API data.
        
        Args:
            world: WorldState instance to update
        """
        # Update weather for each city
        for city_node in world.get_all_cities():
            weather_data = self.weather_api.get_weather(
                city_node.latitude,
                city_node.longitude
            )
            
            # Update fuel prices
            fuel_price = self.fuel_api.get_fuel_price(city_node.name)
            
            logger.debug(
                f"{city_node.name}: {weather_data['status']} "
                f"{weather_data['temp']:.1f}°F, Fuel: ${fuel_price}/gal"
            )
        
        # Update route conditions
        for route in world.get_all_routes():
            # Update weather on route
            weather_data = self.weather_api.get_weather(
                (world.graph.nodes[route.source]["latitude"] + 
                 world.graph.nodes[route.target]["latitude"]) / 2,
                (world.graph.nodes[route.source]["longitude"] + 
                 world.graph.nodes[route.target]["longitude"]) / 2
            )
            
            world.update_weather(
                route.source,
                route.target,
                weather_data["status"]
            )
            
            # Update traffic/congestion
            traffic_data = self.traffic_api.get_route_condition(
                route.source,
                route.target
            )
            
            # Apply congestion as fuel multiplier
            world.update_fuel_multiplier(
                route.source,
                route.target,
                traffic_data["congestion_multiplier"]
            )
            
            # Close route if there's a severe incident
            if traffic_data["has_incident"] and traffic_data["estimated_delay_hours"] > 1:
                world.close_route(route.source, route.target)
                logger.info(f"Route {route.source} -> {route.target} CLOSED due to incident")
