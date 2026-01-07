"""
Schema definitions for MA-GET (Multi-Agent Generative Economic Twin)
Pydantic models for structured agent communication and world state.
"""

from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class NegotiationStatus(str, Enum):
    """Status of a negotiation offer."""
    PENDING = "PENDING"
    COUNTER_OFFER = "COUNTER_OFFER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class WeatherStatus(str, Enum):
    """Weather conditions affecting route edges."""
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    STORM = "STORM"
    FOG = "FOG"
    SEVERE = "SEVERE"


class OrderPriority(str, Enum):
    """Priority levels for shipping orders."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentType(str, Enum):
    """Types of agents in the ecosystem."""
    WAREHOUSE = "WAREHOUSE"
    CARRIER = "CARRIER"
    ENVIRONMENTAL = "ENVIRONMENTAL"


class DealOutcome(str, Enum):
    """Outcome of a completed deal."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CarrierPersona(str, Enum):
    """Market personas for carrier agents."""
    PREMIUM = "PREMIUM"  # SwiftLogistics
    GREEN = "GREEN"      # EcoFreight
    DISCOUNT = "DISCOUNT"  # BudgetTrucking


# =============================================================================
# WORLD STATE MODELS
# =============================================================================

class CityNode(BaseModel):
    """Represents a city node in the logistics network."""
    name: str = Field(..., description="City name")
    latitude: float = Field(..., description="Geographic latitude")
    longitude: float = Field(..., description="Geographic longitude")
    warehouse_capacity: int = Field(default=1000, description="Max warehouse capacity in units")
    current_inventory: int = Field(default=0, description="Current inventory level")
    demand_rate: float = Field(default=1.0, description="Demand multiplier for this city")


class RouteEdge(BaseModel):
    """Represents a highway/route edge between cities."""
    source: str = Field(..., description="Source city name")
    target: str = Field(..., description="Target city name")
    base_distance: float = Field(..., description="Base distance in miles")
    fuel_multiplier: float = Field(default=1.0, ge=0.5, le=3.0, description="Fuel cost multiplier")
    weather_status: WeatherStatus = Field(default=WeatherStatus.CLEAR, description="Current weather")
    congestion_factor: float = Field(default=1.0, ge=0.5, le=2.0, description="Traffic congestion multiplier")
    is_open: bool = Field(default=True, description="Whether the route is passable")


class WorldSnapshot(BaseModel):
    """Complete snapshot of the world state at a point in time."""
    timestamp: datetime = Field(default_factory=datetime.now)
    tick: int = Field(default=0, description="Simulation tick number")
    cities: List[CityNode] = Field(default_factory=list)
    routes: List[RouteEdge] = Field(default_factory=list)


# =============================================================================
# ORDER & SHIPMENT MODELS
# =============================================================================

class Order(BaseModel):
    """Represents a shipping order/package."""
    order_id: str = Field(..., description="Unique order identifier")
    origin: str = Field(..., description="Origin city")
    destination: str = Field(..., description="Destination city")
    weight_kg: float = Field(default=100.0, ge=0.1, description="Package weight in kg")
    volume_m3: float = Field(default=1.0, ge=0.01, description="Package volume in cubic meters")
    priority: OrderPriority = Field(default=OrderPriority.MEDIUM)
    max_budget: float = Field(..., description="Maximum budget the warehouse is willing to pay")
    deadline_hours: float = Field(default=48.0, description="Delivery deadline in hours")
    created_at: datetime = Field(default_factory=datetime.now)


class Shipment(BaseModel):
    """Represents an active shipment in transit."""
    shipment_id: str = Field(..., description="Unique shipment identifier")
    order: Order = Field(..., description="The associated order")
    carrier_id: str = Field(..., description="Assigned carrier agent ID")
    agreed_price: float = Field(..., description="Negotiated price")
    route: List[str] = Field(..., description="Planned route as list of cities")
    eta_hours: float = Field(..., description="Estimated time of arrival in hours")
    status: str = Field(default="IN_TRANSIT")


class DealHistory(BaseModel):
    """Record of a completed deal for reputation tracking."""
    deal_id: str = Field(..., description="Unique deal identifier")
    negotiation_id: str = Field(..., description="Associated negotiation ID")
    warehouse_id: str = Field(..., description="Warehouse agent involved")
    carrier_id: str = Field(..., description="Carrier agent involved")
    order_id: str = Field(..., description="Order that was negotiated")
    
    # Deal details
    agreed_price: float = Field(..., description="Final negotiated price")
    negotiation_rounds: int = Field(..., description="Number of rounds to reach agreement")
    outcome: DealOutcome = Field(..., description="Final outcome of the deal")
    
    # Performance metrics
    on_time_delivery: Optional[bool] = Field(default=None, description="Was delivery on time")
    actual_eta: Optional[float] = Field(default=None, description="Actual delivery time in hours")
    promised_eta: float = Field(..., description="Promised delivery time in hours")
    
    timestamp: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)


class ReputationScore(BaseModel):
    """Reputation score for an agent based on past performance."""
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: AgentType = Field(..., description="Type of agent")
    
    # Aggregate metrics
    total_deals: int = Field(default=0, description="Total number of completed deals")
    successful_deals: int = Field(default=0, description="Number of successful deals")
    failed_deals: int = Field(default=0, description="Number of failed deals")
    
    # Reputation score (0.0 to 1.0)
    overall_score: float = Field(default=1.0, ge=0, le=1, description="Overall reputation score")
    reliability_score: float = Field(default=1.0, ge=0, le=1, description="On-time delivery reliability")
    negotiation_fairness: float = Field(default=1.0, ge=0, le=1, description="Fairness in negotiations")
    
    # Statistics
    avg_negotiation_rounds: float = Field(default=3.0, description="Average rounds to close deal")
    on_time_percentage: float = Field(default=1.0, ge=0, le=1, description="Percentage of on-time deliveries")
    
    last_updated: datetime = Field(default_factory=datetime.now)


# =============================================================================
# NEGOTIATION MODELS
# =============================================================================

class NegotiationOffer(BaseModel):
    """A structured offer in the negotiation protocol."""
    offer_id: str = Field(..., description="Unique offer identifier")
    round_number: int = Field(default=1, ge=1, description="Current negotiation round")
    sender_id: str = Field(..., description="ID of the agent sending the offer")
    sender_type: AgentType = Field(..., description="Type of the sending agent")
    recipient_id: str = Field(..., description="ID of the receiving agent")
    order_id: str = Field(..., description="Order being negotiated")
    
    # Core offer details
    offer_price: float = Field(..., ge=0, description="Proposed price for the shipment")
    reasoning: str = Field(..., description="Agent's reasoning for this offer")
    eta_estimate: float = Field(..., ge=0, description="Estimated delivery time in hours")
    
    # Status and metadata
    status: NegotiationStatus = Field(default=NegotiationStatus.PENDING)
    confidence: float = Field(default=0.8, ge=0, le=1, description="Agent's confidence in offer")
    constraints: Optional[List[str]] = Field(default=None, description="Any constraints or conditions")
    
    timestamp: datetime = Field(default_factory=datetime.now)


class NegotiationResponse(BaseModel):
    """Response to a negotiation offer."""
    response_id: str = Field(..., description="Unique response identifier")
    offer_id: str = Field(..., description="The offer being responded to")
    responder_id: str = Field(..., description="ID of the responding agent")
    responder_type: AgentType = Field(..., description="Type of the responding agent")
    
    # Response details
    status: NegotiationStatus = Field(..., description="Accept, reject, or counter")
    counter_price: Optional[float] = Field(default=None, description="Counter offer price if applicable")
    reasoning: str = Field(..., description="Reasoning for this response")
    counter_eta: Optional[float] = Field(default=None, description="Counter ETA if applicable")
    
    timestamp: datetime = Field(default_factory=datetime.now)


class NegotiationState(BaseModel):
    """Complete state of an ongoing negotiation."""
    negotiation_id: str = Field(..., description="Unique negotiation session ID")
    order: Order = Field(..., description="The order being negotiated")
    warehouse_id: str = Field(..., description="Warehouse agent in negotiation")
    carrier_id: str = Field(..., description="Carrier agent in negotiation")
    
    # Negotiation history
    offers: List[NegotiationOffer] = Field(default_factory=list)
    responses: List[NegotiationResponse] = Field(default_factory=list)
    current_round: int = Field(default=1)
    max_rounds: int = Field(default=5)
    
    # Outcome
    is_complete: bool = Field(default=False)
    final_status: Optional[NegotiationStatus] = Field(default=None)
    agreed_price: Optional[float] = Field(default=None)
    agreed_eta: Optional[float] = Field(default=None)
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)


class MarketplaceAuction(BaseModel):
    """Tracks a competitive bidding auction for an order."""
    auction_id: str = Field(..., description="Unique auction identifier")
    order: Order = Field(..., description="The order being auctioned")
    warehouse_id: str = Field(..., description="Warehouse agent hosting the auction")
    
    # Bidding information
    bids: List[NegotiationOffer] = Field(default_factory=list, description="All bids from carriers")
    participating_carriers: List[str] = Field(default_factory=list, description="Carrier IDs in auction")
    
    # Auction outcome
    is_complete: bool = Field(default=False)
    winner_id: Optional[str] = Field(default=None, description="Winning carrier ID")
    winning_bid: Optional[NegotiationOffer] = Field(default=None)
    selection_reasoning: str = Field(default="", description="Why this carrier was chosen")
    
    # Scoring details
    bid_scores: Dict[str, float] = Field(default_factory=dict, description="Calculated scores for each bid")
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)


# =============================================================================
# AGENT INTERNAL STATE MODELS
# =============================================================================

class AgentMonologue(BaseModel):
    """Internal reasoning/monologue of an agent (for logging)."""
    agent_id: str
    agent_type: AgentType
    timestamp: datetime = Field(default_factory=datetime.now)
    context: str = Field(..., description="What the agent is currently considering")
    reasoning: str = Field(..., description="Step-by-step reasoning")
    decision: str = Field(..., description="The decision or action taken")
    confidence: float = Field(default=0.8, ge=0, le=1)


class WarehouseState(BaseModel):
    """Internal state for a Warehouse Agent."""
    agent_id: str
    location: str = Field(..., description="City where warehouse is located")
    current_inventory: int = Field(default=500)
    pending_orders: List[Order] = Field(default_factory=list)
    active_negotiations: List[str] = Field(default_factory=list)
    budget_remaining: float = Field(default=10000.0)
    urgency_threshold: float = Field(default=0.7, description="When to prioritize speed over cost")
    reputation: ReputationScore = Field(default_factory=lambda: ReputationScore(agent_id="", agent_type=AgentType.WAREHOUSE))


class CarrierState(BaseModel):
    """Internal state for a Carrier Agent."""
    agent_id: str
    fleet_size: int = Field(default=5)
    available_trucks: int = Field(default=5)
    current_location: str = Field(..., description="Current primary location")
    active_shipments: List[str] = Field(default_factory=list)
    profit_target_per_mile: float = Field(default=2.5, description="Target profit per mile")
    fuel_cost_per_mile: float = Field(default=0.50)
    reputation: ReputationScore = Field(default_factory=lambda: ReputationScore(agent_id="", agent_type=AgentType.CARRIER))
    
    # Market persona attributes
    persona: Optional['CarrierPersona'] = Field(default=None, description="Market persona/brand identity")
    company_name: str = Field(default="Generic Carrier", description="Company name")
    speed_priority: float = Field(default=1.0, ge=0.5, le=2.0, description="Speed vs cost tradeoff")
    green_rating: float = Field(default=0.5, ge=0, le=1, description="Environmental friendliness score")


class EnvironmentalState(BaseModel):
    """Internal state for the Environmental Agent."""
    agent_id: str = Field(default="ENV_AGENT_001")
    current_tick: int = Field(default=0)
    chaos_level: float = Field(default=0.2, ge=0, le=1, description="Probability of adverse events")
    active_events: List[str] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=datetime.now)


# =============================================================================
# LANGGRAPH STATE MODEL
# =============================================================================

class GraphState(BaseModel):
    """State object passed through the LangGraph workflow."""
    # Core negotiation state
    negotiation: NegotiationState
    
    # Agent states
    warehouse_state: WarehouseState
    carrier_state: CarrierState
    
    # World context
    world_snapshot: Optional[WorldSnapshot] = None
    route_info: Optional[RouteEdge] = None
    
    # Workflow control
    current_speaker: AgentType = Field(default=AgentType.WAREHOUSE)
    messages: List[str] = Field(default_factory=list)
    error: Optional[str] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True
