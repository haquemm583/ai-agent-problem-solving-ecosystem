"""
Market Heartbeat - Continuous Simulation Engine
Autonomous demand generation and inventory management for MA-GET.
"""

import uuid
import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.core.schema import Order, OrderPriority
from src.core.world import WorldState


logger = logging.getLogger("MA-GET.MarketHeartbeat")


@dataclass
class CityDemandState:
    """Tracks demand state for a city."""
    city_name: str
    current_inventory: int
    warehouse_capacity: int
    demand_rate: float
    inventory_threshold: float = 0.3  # Generate order when below 30%
    last_order_time: Optional[datetime] = None
    total_orders_generated: int = 0
    
    @property
    def inventory_percentage(self) -> float:
        """Calculate inventory as percentage of capacity."""
        if self.warehouse_capacity == 0:
            return 0.0
        return self.current_inventory / self.warehouse_capacity
    
    @property
    def needs_replenishment(self) -> bool:
        """Check if inventory is below threshold."""
        return self.inventory_percentage < self.inventory_threshold


@dataclass
class MarketHeartbeatConfig:
    """Configuration for the Market Heartbeat."""
    tick_interval_seconds: float = 1.0  # Time between simulation ticks
    demand_calculation_interval: int = 1  # Calculate demand every N ticks
    inventory_depletion_rate: float = 0.1  # Percentage depleted per tick
    auto_generate_orders: bool = True
    max_orders_per_tick: int = 3
    priority_distribution: Dict[OrderPriority, float] = field(default_factory=lambda: {
        OrderPriority.LOW: 0.2,
        OrderPriority.MEDIUM: 0.5,
        OrderPriority.HIGH: 0.2,
        OrderPriority.CRITICAL: 0.1
    })


class MarketHeartbeat:
    """
    Continuous simulation engine that autonomously generates demand and orders.
    
    Features:
    - Tracks inventory levels for each city
    - Depletes inventory based on demand rates
    - Autonomously generates orders when inventory falls below threshold
    - Runs in infinite loop until stopped
    """
    
    def __init__(
        self,
        world: WorldState,
        config: Optional[MarketHeartbeatConfig] = None,
        on_order_generated: Optional[Callable[[Order], None]] = None
    ):
        self.world = world
        self.config = config or MarketHeartbeatConfig()
        self.on_order_generated = on_order_generated
        
        # Initialize demand tracking for each city
        self.city_states: Dict[str, CityDemandState] = {}
        self._initialize_city_states()
        
        # Simulation state
        self.is_running = False
        self.current_tick = 0
        self.start_time: Optional[datetime] = None
        self.generated_orders: List[Order] = []
        
        logger.info("Market Heartbeat initialized")
    
    def _initialize_city_states(self):
        """Initialize demand state tracking for all cities."""
        cities = self.world.get_all_cities()
        for city in cities:
            self.city_states[city.name] = CityDemandState(
                city_name=city.name,
                current_inventory=city.current_inventory,
                warehouse_capacity=city.warehouse_capacity,
                demand_rate=city.demand_rate
            )
            logger.info(
                f"Initialized {city.name}: "
                f"{city.current_inventory}/{city.warehouse_capacity} units "
                f"(demand rate: {city.demand_rate:.1f}x)"
            )
    
    def calculate_demand_for_city(self, city_name: str) -> float:
        """
        Calculate current demand rate for a city.
        
        Factors:
        - Base demand rate from world state
        - Current inventory levels (lower inventory = higher urgency)
        - Time since last order
        
        Returns:
            Demand score (0.0 to 1.0)
        """
        state = self.city_states.get(city_name)
        if not state:
            return 0.0
        
        # Base demand from world
        base_demand = state.demand_rate
        
        # Inventory urgency factor (inverse of inventory percentage)
        inventory_urgency = 1.0 - state.inventory_percentage
        
        # Time urgency (increases if no order recently)
        time_urgency = 1.0
        if state.last_order_time:
            hours_since_order = (datetime.now() - state.last_order_time).total_seconds() / 3600
            time_urgency = min(hours_since_order / 24.0, 1.0)  # Max at 24 hours
        
        # Combined demand score
        demand_score = (base_demand * 0.4) + (inventory_urgency * 0.4) + (time_urgency * 0.2)
        
        return min(demand_score, 1.0)
    
    def deplete_inventory(self, city_name: str, amount: Optional[float] = None):
        """
        Deplete inventory for a city based on demand rate.
        
        Args:
            city_name: Name of the city
            amount: Amount to deplete (if None, uses config depletion rate)
        """
        state = self.city_states.get(city_name)
        if not state:
            return
        
        if amount is None:
            # Calculate depletion based on demand rate and config
            depletion = int(
                state.warehouse_capacity * 
                self.config.inventory_depletion_rate * 
                state.demand_rate
            )
        else:
            depletion = int(amount)
        
        # Apply depletion
        state.current_inventory = max(0, state.current_inventory - depletion)
        
        # Update world state
        if city_name in self.world.graph.nodes:
            self.world.graph.nodes[city_name]['current_inventory'] = state.current_inventory
    
    def replenish_inventory(self, city_name: str, amount: int):
        """
        Replenish inventory for a city (when order is fulfilled).
        
        Args:
            city_name: Name of the city
            amount: Amount to add to inventory
        """
        state = self.city_states.get(city_name)
        if not state:
            return
        
        # Add inventory, capped at capacity
        state.current_inventory = min(
            state.warehouse_capacity,
            state.current_inventory + amount
        )
        
        # Update world state
        if city_name in self.world.graph.nodes:
            self.world.graph.nodes[city_name]['current_inventory'] = state.current_inventory
        
        logger.info(
            f"📦 Replenished {city_name}: +{amount} units "
            f"(now {state.current_inventory}/{state.warehouse_capacity})"
        )
    
    def generate_order_for_city(
        self,
        destination_city: str,
        priority: Optional[OrderPriority] = None
    ) -> Optional[Order]:
        """
        Generate a new order for a city that needs replenishment.
        
        Args:
            destination_city: City needing inventory
            priority: Order priority (auto-determined if None)
            
        Returns:
            Generated Order or None if unable to generate
        """
        state = self.city_states.get(destination_city)
        if not state:
            logger.warning(f"Cannot generate order: {destination_city} not found")
            return None
        
        # Determine priority based on inventory urgency
        if priority is None:
            inv_pct = state.inventory_percentage
            if inv_pct < 0.1:
                priority = OrderPriority.CRITICAL
            elif inv_pct < 0.2:
                priority = OrderPriority.HIGH
            elif inv_pct < 0.3:
                priority = OrderPriority.MEDIUM
            else:
                priority = OrderPriority.LOW
        
        # Select origin city (different from destination)
        available_cities = [
            name for name in self.city_states.keys() 
            if name != destination_city
        ]
        if not available_cities:
            return None
        
        # Choose origin with highest inventory
        origin_city = max(
            available_cities,
            key=lambda c: self.city_states[c].current_inventory
        )
        
        # Calculate order parameters
        shortage = state.warehouse_capacity - state.current_inventory
        weight_kg = min(shortage * 50, 1000.0)  # Assume 50kg per unit, max 1000kg
        volume_m3 = weight_kg / 200.0  # Rough density estimate
        
        # Calculate budget (with urgency multiplier)
        path, distance = self.world.get_shortest_path(origin_city, destination_city)
        base_budget = distance * 1.5  # $1.50 per mile base
        urgency_multiplier = {
            OrderPriority.CRITICAL: 2.0,
            OrderPriority.HIGH: 1.5,
            OrderPriority.MEDIUM: 1.2,
            OrderPriority.LOW: 1.0
        }.get(priority, 1.0)
        max_budget = base_budget * urgency_multiplier
        
        # Deadline based on priority
        deadline_hours = {
            OrderPriority.CRITICAL: 6.0,
            OrderPriority.HIGH: 12.0,
            OrderPriority.MEDIUM: 24.0,
            OrderPriority.LOW: 48.0
        }.get(priority, 24.0)
        
        # Create order
        order = Order(
            order_id=f"ORD-AUTO-{uuid.uuid4().hex[:6].upper()}",
            origin=origin_city,
            destination=destination_city,
            weight_kg=weight_kg,
            volume_m3=volume_m3,
            priority=priority,
            max_budget=max_budget,
            deadline_hours=deadline_hours
        )
        
        # Update state
        state.last_order_time = datetime.now()
        state.total_orders_generated += 1
        self.generated_orders.append(order)
        
        logger.info(
            f"🆕 Generated Order {order.order_id}: "
            f"{origin_city} → {destination_city} "
            f"({priority.value}, ${max_budget:.2f}, {weight_kg:.0f}kg)"
        )
        
        # Callback if provided
        if self.on_order_generated:
            self.on_order_generated(order)
        
        return order
    
    def tick(self) -> List[Order]:
        """
        Execute one simulation tick.
        
        Returns:
            List of newly generated orders
        """
        self.current_tick += 1
        new_orders = []
        
        # Deplete inventory for all cities
        for city_name in self.city_states.keys():
            self.deplete_inventory(city_name)
        
        # Check demand and generate orders if needed
        if self.config.auto_generate_orders:
            orders_this_tick = 0
            
            for city_name, state in self.city_states.items():
                if orders_this_tick >= self.config.max_orders_per_tick:
                    break
                
                if state.needs_replenishment:
                    demand_score = self.calculate_demand_for_city(city_name)
                    
                    # Generate order with probability based on demand
                    if demand_score > 0.5:  # Threshold for order generation
                        order = self.generate_order_for_city(city_name)
                        if order:
                            new_orders.append(order)
                            orders_this_tick += 1
        
        return new_orders
    
    def run(self, max_ticks: Optional[int] = None):
        """
        Run the heartbeat in a continuous loop.
        
        Args:
            max_ticks: Maximum number of ticks to run (None for infinite)
        """
        self.is_running = True
        self.start_time = datetime.now()
        
        logger.info("❤️  Market Heartbeat started")
        print(f"\n{'='*80}")
        print("❤️  MARKET HEARTBEAT - AUTONOMOUS SIMULATION STARTED")
        print(f"{'='*80}")
        print(f"Tick Interval: {self.config.tick_interval_seconds}s")
        print(f"Auto-generate Orders: {self.config.auto_generate_orders}")
        print(f"Max Orders/Tick: {self.config.max_orders_per_tick}")
        print(f"{'='*80}\n")
        
        try:
            while self.is_running:
                # Execute tick
                new_orders = self.tick()
                
                # Log tick status
                if self.current_tick % 10 == 0 or new_orders:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    print(f"\n[Tick {self.current_tick}] Elapsed: {elapsed:.1f}s")
                    
                    # Show inventory status
                    for city_name, state in self.city_states.items():
                        status_icon = "🔴" if state.needs_replenishment else "🟢"
                        print(
                            f"  {status_icon} {city_name}: "
                            f"{state.current_inventory}/{state.warehouse_capacity} "
                            f"({state.inventory_percentage*100:.1f}%)"
                        )
                    
                    if new_orders:
                        print(f"\n  📦 Generated {len(new_orders)} new orders:")
                        for order in new_orders:
                            print(f"     • {order.order_id}: {order.origin} → {order.destination}")
                
                # Check stop condition
                if max_ticks and self.current_tick >= max_ticks:
                    logger.info(f"Reached max ticks: {max_ticks}")
                    break
                
                # Wait for next tick
                time.sleep(self.config.tick_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Heartbeat stopped by user")
            print("\n\n⏸️  Heartbeat stopped by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the heartbeat."""
        self.is_running = False
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print(f"\n{'='*80}")
        print("❤️  MARKET HEARTBEAT - SIMULATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Ticks: {self.current_tick}")
        print(f"Elapsed Time: {elapsed:.1f}s")
        print(f"Orders Generated: {len(self.generated_orders)}")
        print(f"\nCity Statistics:")
        for city_name, state in self.city_states.items():
            print(
                f"  {city_name}: "
                f"{state.current_inventory}/{state.warehouse_capacity} units, "
                f"{state.total_orders_generated} orders generated"
            )
        print(f"{'='*80}\n")
        
        logger.info(
            f"Heartbeat stopped. "
            f"Ticks: {self.current_tick}, "
            f"Orders: {len(self.generated_orders)}"
        )
    
    def get_statistics(self) -> Dict:
        """Get current heartbeat statistics."""
        return {
            "current_tick": self.current_tick,
            "is_running": self.is_running,
            "total_orders_generated": len(self.generated_orders),
            "elapsed_time_seconds": (
                (datetime.now() - self.start_time).total_seconds() 
                if self.start_time else 0
            ),
            "city_states": {
                name: {
                    "inventory": state.current_inventory,
                    "capacity": state.warehouse_capacity,
                    "inventory_percentage": state.inventory_percentage,
                    "needs_replenishment": state.needs_replenishment,
                    "orders_generated": state.total_orders_generated
                }
                for name, state in self.city_states.items()
            }
        }


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    # Create world
    world = WorldState()
    
    # Create heartbeat
    config = MarketHeartbeatConfig(
        tick_interval_seconds=2.0,
        inventory_depletion_rate=0.05,
        auto_generate_orders=True,
        max_orders_per_tick=2
    )
    
    def on_order_callback(order: Order):
        """Callback when order is generated."""
        print(f"\n🔔 ORDER CALLBACK: {order.order_id}")
    
    heartbeat = MarketHeartbeat(world, config, on_order_generated=on_order_callback)
    
    # Run for limited time
    print("Running heartbeat for 20 ticks...")
    heartbeat.run(max_ticks=20)
    
    # Print statistics
    stats = heartbeat.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   Total Orders: {stats['total_orders_generated']}")
    print(f"   Total Ticks: {stats['current_tick']}")
