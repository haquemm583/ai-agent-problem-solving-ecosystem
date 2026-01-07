"""
Agent Logic and Prompts for MA-GET
Warehouse and Carrier agents with LangGraph integration.
"""

import uuid
import logging
import os
from typing import Dict, Any, Optional, Literal
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from dotenv import load_dotenv

from schema import (
    AgentType, NegotiationStatus, NegotiationOffer, NegotiationResponse,
    NegotiationState, WarehouseState, CarrierState, AgentMonologue,
    GraphState, Order, OrderPriority
)
from world import WorldState, calculate_fair_price_range, calculate_shipping_cost

# Load environment variables
load_dotenv()

# Import event logging
try:
    from event_log import log_agent_monologue, log_offer, log_response
    EVENT_LOGGING_ENABLED = True
except ImportError:
    EVENT_LOGGING_ENABLED = False


# =============================================================================
# RICH LOGGING SETUP
# =============================================================================

class AgentLogger:
    """Rich logging for agent internal monologues."""
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"MA-GET.{agent_type.value}")
    
    def _get_emoji(self) -> str:
        return {
            AgentType.WAREHOUSE: "🏭",
            AgentType.CARRIER: "🚚",
            AgentType.ENVIRONMENTAL: "🌍"
        }.get(self.agent_type, "🤖")
    
    def monologue(self, context: str, reasoning: str, decision: str, confidence: float = 0.8):
        """Log an agent's internal monologue."""
        emoji = self._get_emoji()
        
        print(f"\n{'='*70}")
        print(f"{emoji} INTERNAL MONOLOGUE: {self.agent_id} ({self.agent_type.value})")
        print(f"{'='*70}")
        print(f"\n📋 CONTEXT:")
        print(f"   {context}")
        print(f"\n🧠 REASONING:")
        for line in reasoning.split('\n'):
            print(f"   {line}")
        print(f"\n✅ DECISION (confidence: {confidence:.0%}):")
        print(f"   {decision}")
        print(f"{'='*70}\n")
        
        # Also log structured data
        monologue = AgentMonologue(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            context=context,
            reasoning=reasoning,
            decision=decision,
            confidence=confidence
        )
        self.logger.info(f"Monologue: {monologue.model_dump_json()}")
        
        # Log to event system for dashboard
        if EVENT_LOGGING_ENABLED:
            log_agent_monologue(
                self.agent_id,
                self.agent_type.value,
                context,
                reasoning,
                decision,
                confidence
            )
        
        return monologue
    
    def action(self, action: str, details: str = ""):
        """Log an agent action."""
        emoji = self._get_emoji()
        print(f"{emoji} [{self.agent_id}] {action}")
        if details:
            print(f"   └─ {details}")


# =============================================================================
# AGENT PROMPTS
# =============================================================================

WAREHOUSE_SYSTEM_PROMPT = """You are a Warehouse Agent managing inventory and shipping logistics.

OBJECTIVE: Minimize shipping costs while meeting delivery deadlines.

CONTEXT:
- Location: {location}
- Current Budget: ${budget_remaining:.2f}
- Urgency Threshold: {urgency_threshold:.0%}

ORDER DETAILS:
- Order ID: {order_id}
- Origin: {origin} → Destination: {destination}
- Weight: {weight_kg}kg
- Priority: {priority}
- Deadline: {deadline_hours} hours
- Maximum Budget: ${max_budget:.2f}

ROUTE INFORMATION:
- Distance: {distance:.0f} miles
- Fair Price Range: ${min_fair_price:.2f} - ${max_fair_price:.2f}
- Weather: {weather}
- Fuel Multiplier: {fuel_multiplier:.2f}x

NEGOTIATION STATE:
- Current Round: {current_round}/{max_rounds}
- Previous Offers: {previous_offers}

INSTRUCTIONS:
1. Analyze the carrier's offer (if any)
2. Consider your budget constraints and urgency
3. Decide whether to: ACCEPT, REJECT, or make a COUNTER_OFFER
4. Provide clear reasoning for your decision
5. If making a counter offer, propose a fair price within your budget

Respond with your decision in this exact JSON format:
{{
    "status": "ACCEPTED" | "REJECTED" | "COUNTER_OFFER",
    "offer_price": <your offer price as a number>,
    "reasoning": "<your detailed reasoning>",
    "eta_estimate": <expected delivery time in hours>,
    "confidence": <0.0 to 1.0>
}}"""

CARRIER_SYSTEM_PROMPT = """You are a Carrier Agent managing a fleet of trucks.

OBJECTIVE: Maximize profit per mile while maintaining reputation.

CONTEXT:
- Fleet Size: {fleet_size} trucks
- Available Trucks: {available_trucks}
- Current Location: {current_location}
- Target Profit/Mile: ${profit_target_per_mile:.2f}
- Fuel Cost/Mile: ${fuel_cost_per_mile:.2f}
- Reputation Score: {reputation_score:.0%}

ORDER DETAILS:
- Order ID: {order_id}
- Route: {origin} → {destination}
- Weight: {weight_kg}kg
- Priority: {priority}
- Client's Max Budget: ${max_budget:.2f}

ROUTE INFORMATION:
- Distance: {distance:.0f} miles
- Fair Price Range: ${min_fair_price:.2f} - ${max_fair_price:.2f}
- Weather: {weather}
- Fuel Multiplier: {fuel_multiplier:.2f}x

COST ANALYSIS:
- Base Fuel Cost: ${fuel_cost:.2f}
- Minimum Acceptable: ${minimum_price:.2f}
- Target Price: ${target_price:.2f}

NEGOTIATION STATE:
- Current Round: {current_round}/{max_rounds}
- Previous Offers: {previous_offers}

INSTRUCTIONS:
1. Analyze the warehouse's offer (if any)
2. Calculate your costs and desired profit margin
3. Decide whether to: ACCEPT, REJECT, or make a COUNTER_OFFER
4. Consider that repeated rejections may lose the deal
5. Factor in weather and fuel costs

Respond with your decision in this exact JSON format:
{{
    "status": "ACCEPTED" | "REJECTED" | "COUNTER_OFFER",
    "offer_price": <your offer price as a number>,
    "reasoning": "<your detailed reasoning>",
    "eta_estimate": <expected delivery time in hours>,
    "confidence": <0.0 to 1.0>
}}"""


# =============================================================================
# AGENT CLASSES
# =============================================================================

class BaseAgent:
    """Base class for all agents."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        llm: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.llm = llm
        self.logger = AgentLogger(agent_id, agent_type)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response."""
        import json
        import re
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback defaults
        return {
            "status": "COUNTER_OFFER",
            "offer_price": 0,
            "reasoning": response,
            "eta_estimate": 24.0,
            "confidence": 0.5
        }


class WarehouseAgent(BaseAgent):
    """Warehouse Agent: Manages inventory and bids for shipping."""
    
    def __init__(
        self,
        agent_id: str,
        location: str,
        llm: Optional[Any] = None,
        budget: float = 10000.0,
        urgency_threshold: float = 0.7,
        use_llm: bool = True
    ):
        # Initialize LLM if not provided
        if llm is None and use_llm:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                    llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
                    print(f"✅ LLM enabled for {agent_id} ({model})")
                else:
                    use_llm = False
                    print(f"⚠️  No OPENAI_API_KEY found - using rule-based logic for {agent_id}")
            except Exception as e:
                use_llm = False
                print(f"⚠️  LLM initialization failed: {e} - using rule-based logic")
        
        super().__init__(agent_id, AgentType.WAREHOUSE, llm)
        self.state = WarehouseState(
            agent_id=agent_id,
            location=location,
            budget_remaining=budget,
            urgency_threshold=urgency_threshold
        )
        self.use_llm = use_llm and llm is not None
    
    def create_initial_offer(
        self,
        order: Order,
        world: WorldState,
        negotiation_id: str
    ) -> NegotiationOffer:
        """Create the initial offer to start negotiations."""
        # Get route information
        route = world.get_route(order.origin, order.destination)
        if route:
            distance = route.base_distance
            fuel_mult = route.fuel_multiplier
            weather = route.weather_status.value
        else:
            path, distance = world.get_shortest_path(order.origin, order.destination)
            fuel_mult = 1.0
            weather = "CLEAR"
        
        min_price, max_price = calculate_fair_price_range(
            world, order.origin, order.destination, order.weight_kg
        )
        
        # Calculate ETA
        eta = world.estimate_travel_time(order.origin, order.destination)
        
        # Use LLM if available
        if self.use_llm and self.llm:
            prompt = WAREHOUSE_SYSTEM_PROMPT.format(
                location=self.state.location,
                budget_remaining=self.state.budget_remaining,
                urgency_threshold=self.state.urgency_threshold,
                order_id=order.order_id,
                origin=order.origin,
                destination=order.destination,
                weight_kg=order.weight_kg,
                priority=order.priority.value,
                deadline_hours=order.deadline_hours,
                max_budget=order.max_budget,
                distance=distance,
                min_fair_price=min_price,
                max_fair_price=max_price,
                weather=weather,
                fuel_multiplier=fuel_mult,
                current_round=1,
                max_rounds=5,
                previous_offers="None (initial offer)"
            )
            
            try:
                response = self.llm.invoke(prompt)
                result = self._parse_llm_response(response.content)
                
                initial_offer_price = result.get("offer_price", min_price * 1.3)
                reasoning = result.get("reasoning", "LLM-generated offer")
                confidence = result.get("confidence", 0.75)
            except Exception as e:
                # Fallback to rule-based
                initial_offer_price = min_price + (max_price - min_price) * 0.3
                initial_offer_price = min(initial_offer_price, order.max_budget * 0.7)
                reasoning = f"Rule-based offer (LLM error: {str(e)})"
                confidence = 0.75
        else:
            # Rule-based fallback
            initial_offer_price = min_price + (max_price - min_price) * 0.3
            initial_offer_price = min(initial_offer_price, order.max_budget * 0.7)
            reasoning = (
                f"Starting negotiation for {order.origin} → {order.destination}.\n"
                f"Distance: {distance:.0f} miles, Fair range: ${min_price:.2f}-${max_price:.2f}.\n"
                f"Starting with conservative offer at ${initial_offer_price:.2f} "
                f"(30% of fair range, 70% of max budget).\n"
                f"This leaves room for negotiation while showing serious intent."
            )
            confidence = 0.75
        
        self.logger.monologue(
            context=f"Creating initial offer for Order {order.order_id}",
            reasoning=reasoning,
            decision=f"Initial offer: ${initial_offer_price:.2f} with ETA {eta:.1f}h",
            confidence=confidence
        )
        
        return NegotiationOffer(
            offer_id=f"OFF-{uuid.uuid4().hex[:8]}",
            round_number=1,
            sender_id=self.agent_id,
            sender_type=AgentType.WAREHOUSE,
            recipient_id="",  # To be filled
            order_id=order.order_id,
            offer_price=initial_offer_price,
            reasoning=reasoning,
            eta_estimate=eta,
            status=NegotiationStatus.PENDING,
            confidence=confidence
        )
    
    def respond_to_offer(
        self,
        incoming_offer: NegotiationOffer,
        order: Order,
        world: WorldState,
        current_round: int,
        max_rounds: int
    ) -> NegotiationResponse:
        """Respond to a carrier's offer."""
        # Get route information
        route = world.get_route(order.origin, order.destination)
        if route:
            distance = route.base_distance
            weather = route.weather_status.value
            fuel_mult = route.fuel_multiplier
        else:
            distance = 200.0
            weather = "CLEAR"
            fuel_mult = 1.0
        
        min_price, max_price = calculate_fair_price_range(
            world, order.origin, order.destination, order.weight_kg
        )
        
        offered_price = incoming_offer.offer_price
        rounds_left = max_rounds - current_round
        
        # Use LLM if available
        if self.use_llm and self.llm:
            # Build previous offers history
            previous_offers = f"Carrier offered: ${offered_price:.2f}"
            
            prompt = WAREHOUSE_SYSTEM_PROMPT.format(
                location=self.state.location,
                budget_remaining=self.state.budget_remaining,
                urgency_threshold=self.state.urgency_threshold,
                order_id=order.order_id,
                origin=order.origin,
                destination=order.destination,
                weight_kg=order.weight_kg,
                priority=order.priority.value,
                deadline_hours=order.deadline_hours,
                max_budget=order.max_budget,
                distance=distance,
                min_fair_price=min_price,
                max_fair_price=max_price,
                weather=weather,
                fuel_multiplier=fuel_mult,
                current_round=current_round,
                max_rounds=max_rounds,
                previous_offers=previous_offers
            )
            
            try:
                response = self.llm.invoke(prompt)
                result = self._parse_llm_response(response.content)
                
                status_str = result.get("status", "COUNTER_OFFER")
                status = NegotiationStatus(status_str)
                counter_price = result.get("offer_price", offered_price * 0.9)
                reasoning = result.get("reasoning", "LLM-generated response")
                confidence = result.get("confidence", 0.7)
            except Exception as e:
                # Fallback to rule-based
                urgency = 1.0 - (rounds_left / max_rounds)
                acceptable_price = min_price + (max_price - min_price) * (0.5 + urgency * 0.3)
                
                if offered_price <= acceptable_price and offered_price <= order.max_budget:
                    status = NegotiationStatus.ACCEPTED
                    counter_price = offered_price
                    reasoning = f"Rule-based: Accepting ${offered_price:.2f} (LLM error: {str(e)})"
                    confidence = 0.9
                else:
                    status = NegotiationStatus.COUNTER_OFFER
                    counter_price = offered_price * (0.85 + urgency * 0.1)
                    counter_price = min(counter_price, order.max_budget)
                    reasoning = f"Rule-based: Counter at ${counter_price:.2f}"
                    confidence = 0.7
        else:
            # Rule-based fallback
            urgency = 1.0 - (rounds_left / max_rounds)
            acceptable_price = min_price + (max_price - min_price) * (0.5 + urgency * 0.3)
            
            if offered_price <= acceptable_price and offered_price <= order.max_budget:
                status = NegotiationStatus.ACCEPTED
                counter_price = offered_price
                reasoning = (
                    f"Carrier's offer of ${offered_price:.2f} is acceptable.\n"
                    f"It's within our budget (${order.max_budget:.2f}) and below threshold (${acceptable_price:.2f}).\n"
                    f"With {rounds_left} rounds left, this is a fair deal."
                )
                confidence = 0.9
            elif offered_price > order.max_budget:
                status = NegotiationStatus.COUNTER_OFFER
                counter_price = min(order.max_budget * 0.95, max_price)
                reasoning = (
                    f"Carrier's offer (${offered_price:.2f}) exceeds our budget (${order.max_budget:.2f}).\n"
                    f"Counter-offering near our maximum at ${counter_price:.2f}.\n"
                    f"This is our best possible offer."
                )
                confidence = 0.6
            else:
                status = NegotiationStatus.COUNTER_OFFER
                counter_price = offered_price * (0.85 + urgency * 0.1)
                counter_price = min(counter_price, order.max_budget)
                reasoning = (
                    f"Carrier's offer (${offered_price:.2f}) is above our preferred range.\n"
                    f"Counter-offering at ${counter_price:.2f} ({(counter_price/offered_price)*100:.0f}% of their ask).\n"
                    f"Urgency factor: {urgency:.0%}, {rounds_left} rounds remaining."
                )
                confidence = 0.7
        
        self.logger.monologue(
            context=f"Responding to carrier offer of ${offered_price:.2f} (Round {current_round})",
            reasoning=reasoning,
            decision=f"{status.value}: ${counter_price:.2f}",
            confidence=confidence
        )
        
        return NegotiationResponse(
            response_id=f"RES-{uuid.uuid4().hex[:8]}",
            offer_id=incoming_offer.offer_id,
            responder_id=self.agent_id,
            responder_type=AgentType.WAREHOUSE,
            status=status,
            counter_price=counter_price if status == NegotiationStatus.COUNTER_OFFER else None,
            reasoning=reasoning,
            counter_eta=incoming_offer.eta_estimate
        )


class CarrierAgent(BaseAgent):
    """Carrier Agent: Manages fleet and maximizes profit."""
    
    def __init__(
        self,
        agent_id: str,
        location: str,
        llm: Optional[Any] = None,
        fleet_size: int = 5,
        profit_target: float = 2.5,
        use_llm: bool = True
    ):
        # Initialize LLM if not provided
        if llm is None and use_llm:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                    llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
                    print(f"✅ LLM enabled for {agent_id} ({model})")
                else:
                    use_llm = False
                    print(f"⚠️  No OPENAI_API_KEY found - using rule-based logic for {agent_id}")
            except Exception as e:
                use_llm = False
                print(f"⚠️  LLM initialization failed: {e} - using rule-based logic")
        
        super().__init__(agent_id, AgentType.CARRIER, llm)
        self.state = CarrierState(
            agent_id=agent_id,
            fleet_size=fleet_size,
            available_trucks=fleet_size,
            current_location=location,
            profit_target_per_mile=profit_target
        )
        self.use_llm = use_llm and llm is not None
    
    def respond_to_offer(
        self,
        incoming_offer: NegotiationOffer,
        order: Order,
        world: WorldState,
        current_round: int,
        max_rounds: int
    ) -> NegotiationResponse:
        """Respond to a warehouse's offer."""
        # Get route information
        route = world.get_route(order.origin, order.destination)
        if route:
            distance = route.base_distance
            fuel_mult = route.fuel_multiplier
            weather = route.weather_status.value
        else:
            path, distance = world.get_shortest_path(order.origin, order.destination)
            fuel_mult = 1.0
            weather = "CLEAR"
        
        # Calculate costs
        fuel_cost = distance * self.state.fuel_cost_per_mile * fuel_mult
        minimum_price = fuel_cost * 1.2  # 20% margin minimum
        target_price = distance * self.state.profit_target_per_mile * fuel_mult
        
        offered_price = incoming_offer.offer_price
        
        # Decision logic with diminishing demands
        rounds_left = max_rounds - current_round
        flexibility = 1.0 - (rounds_left / max_rounds) * 0.3  # More flexible as rounds progress
        
        adjusted_minimum = minimum_price * (0.9 + 0.1 * (rounds_left / max_rounds))
        adjusted_target = target_price * flexibility
        
        if offered_price >= adjusted_target:
            status = NegotiationStatus.ACCEPTED
            counter_price = offered_price
            reasoning = (
                f"Warehouse offers ${offered_price:.2f}, meeting our target (${adjusted_target:.2f}).\n"
                f"Profit margin: ${offered_price - fuel_cost:.2f} ({((offered_price-fuel_cost)/fuel_cost)*100:.0f}% above costs).\n"
                f"Accepting this profitable deal."
            )
            confidence = 0.95
        elif offered_price < adjusted_minimum:
            if rounds_left <= 1:
                # Last round, accept if above absolute minimum
                if offered_price >= minimum_price * 0.9:
                    status = NegotiationStatus.ACCEPTED
                    counter_price = offered_price
                    reasoning = (
                        f"Final round: accepting ${offered_price:.2f} despite being below target.\n"
                        f"Still covers costs (${fuel_cost:.2f}) with slim margin.\n"
                        f"Better than losing the order entirely."
                    )
                    confidence = 0.6
                else:
                    status = NegotiationStatus.REJECTED
                    counter_price = minimum_price
                    reasoning = (
                        f"Cannot accept ${offered_price:.2f} - below our minimum (${minimum_price:.2f}).\n"
                        f"Would result in a loss of ${fuel_cost - offered_price:.2f}.\n"
                        f"Rejecting this unprofitable offer."
                    )
                    confidence = 0.8
            else:
                status = NegotiationStatus.COUNTER_OFFER
                # Ask for target but show willingness to negotiate
                counter_price = adjusted_target * 0.95
                reasoning = (
                    f"Warehouse offer (${offered_price:.2f}) is below our minimum (${adjusted_minimum:.2f}).\n"
                    f"Counter-offering at ${counter_price:.2f} (5% below target).\n"
                    f"Costs: fuel ${fuel_cost:.2f}, weather factor: {weather}."
                )
                confidence = 0.7
        else:
            status = NegotiationStatus.COUNTER_OFFER
            # Between minimum and target - find middle ground
            counter_price = (offered_price + adjusted_target) / 2
            reasoning = (
                f"Warehouse offers ${offered_price:.2f}, between our minimum and target.\n"
                f"Counter-offering at midpoint: ${counter_price:.2f}.\n"
                f"This ensures profit while showing negotiation goodwill."
            )
            confidence = 0.75
        
        # Calculate ETA
        eta = world.estimate_travel_time(order.origin, order.destination)
        
        # Use LLM if available
        if self.use_llm and self.llm:
            previous_offers = f"Warehouse offered: ${offered_price:.2f}"
            min_fair, max_fair = calculate_fair_price_range(world, order.origin, order.destination, order.weight_kg)
            
            prompt = CARRIER_SYSTEM_PROMPT.format(
                fleet_size=self.state.fleet_size,
                available_trucks=self.state.available_trucks,
                current_location=self.state.current_location,
                profit_target_per_mile=self.state.profit_target_per_mile,
                fuel_cost_per_mile=self.state.fuel_cost_per_mile,
                reputation_score=self.state.reputation_score,
                order_id=order.order_id,
                origin=order.origin,
                destination=order.destination,
                weight_kg=order.weight_kg,
                priority=order.priority.value,
                max_budget=order.max_budget,
                distance=distance,
                min_fair_price=min_fair,
                max_fair_price=max_fair,
                weather=weather,
                fuel_multiplier=fuel_mult,
                fuel_cost=fuel_cost,
                minimum_price=minimum_price,
                target_price=target_price,
                current_round=current_round,
                max_rounds=max_rounds,
                previous_offers=previous_offers
            )
            
            try:
                response = self.llm.invoke(prompt)
                result = self._parse_llm_response(response.content)
                
                status_str = result.get("status", "COUNTER_OFFER")
                status = NegotiationStatus(status_str)
                counter_price = result.get("offer_price", target_price)
                reasoning = result.get("reasoning", "LLM-generated response")
                confidence = result.get("confidence", 0.75)
            except Exception as e:
                # Keep the rule-based decision already calculated
                pass
        
        self.logger.monologue(
            context=f"Evaluating warehouse offer of ${offered_price:.2f} (Round {current_round})",
            reasoning=reasoning,
            decision=f"{status.value}: ${counter_price:.2f}",
            confidence=confidence
        )
        
        return NegotiationResponse(
            response_id=f"RES-{uuid.uuid4().hex[:8]}",
            offer_id=incoming_offer.offer_id,
            responder_id=self.agent_id,
            responder_type=AgentType.CARRIER,
            status=status,
            counter_price=counter_price if status == NegotiationStatus.COUNTER_OFFER else None,
            reasoning=reasoning,
            counter_eta=eta
        )


# =============================================================================
# LANGGRAPH WORKFLOW
# =============================================================================

def create_negotiation_graph(
    warehouse: WarehouseAgent,
    carrier: CarrierAgent,
    world: WorldState
) -> StateGraph:
    """Create a LangGraph workflow for agent negotiation."""
    
    # Define the graph
    workflow = StateGraph(GraphState)
    
    # Node: Warehouse makes/responds to offer
    def warehouse_node(state: GraphState) -> GraphState:
        """Warehouse agent's turn."""
        negotiation = state.negotiation
        order = negotiation.order
        
        warehouse.logger.action("Taking turn", f"Round {negotiation.current_round}")
        
        if not negotiation.offers:
            # First move - create initial offer
            offer = warehouse.create_initial_offer(order, world, negotiation.negotiation_id)
            offer.recipient_id = carrier.agent_id
            negotiation.offers.append(offer)
            state.messages.append(f"Warehouse initial offer: ${offer.offer_price:.2f}")
        else:
            # Respond to carrier's last response
            last_response = negotiation.responses[-1] if negotiation.responses else None
            if last_response and last_response.status == NegotiationStatus.COUNTER_OFFER:
                # Create offer from carrier's counter
                carrier_offer = NegotiationOffer(
                    offer_id=f"OFF-{uuid.uuid4().hex[:8]}",
                    round_number=negotiation.current_round,
                    sender_id=carrier.agent_id,
                    sender_type=AgentType.CARRIER,
                    recipient_id=warehouse.agent_id,
                    order_id=order.order_id,
                    offer_price=last_response.counter_price,
                    reasoning=last_response.reasoning,
                    eta_estimate=last_response.counter_eta or 24.0,
                    status=NegotiationStatus.PENDING
                )
                
                response = warehouse.respond_to_offer(
                    carrier_offer, order, world,
                    negotiation.current_round, negotiation.max_rounds
                )
                negotiation.responses.append(response)
                
                if response.status == NegotiationStatus.ACCEPTED:
                    negotiation.is_complete = True
                    negotiation.final_status = NegotiationStatus.ACCEPTED
                    negotiation.agreed_price = carrier_offer.offer_price
                    negotiation.agreed_eta = carrier_offer.eta_estimate
                    state.messages.append(f"Warehouse ACCEPTS ${carrier_offer.offer_price:.2f}")
                else:
                    state.messages.append(f"Warehouse counters: ${response.counter_price:.2f}")
        
        state.current_speaker = AgentType.CARRIER
        state.negotiation = negotiation
        return state
    
    # Node: Carrier responds to offer
    def carrier_node(state: GraphState) -> GraphState:
        """Carrier agent's turn."""
        negotiation = state.negotiation
        order = negotiation.order
        
        carrier.logger.action("Taking turn", f"Round {negotiation.current_round}")
        
        # Get the last offer/counter from warehouse
        if negotiation.responses:
            last_response = negotiation.responses[-1]
            if last_response.responder_type == AgentType.WAREHOUSE:
                offer_price = last_response.counter_price or negotiation.offers[-1].offer_price
            else:
                offer_price = negotiation.offers[-1].offer_price
        else:
            offer_price = negotiation.offers[-1].offer_price
        
        warehouse_offer = NegotiationOffer(
            offer_id=f"OFF-{uuid.uuid4().hex[:8]}",
            round_number=negotiation.current_round,
            sender_id=warehouse.agent_id,
            sender_type=AgentType.WAREHOUSE,
            recipient_id=carrier.agent_id,
            order_id=order.order_id,
            offer_price=offer_price,
            reasoning="",
            eta_estimate=24.0,
            status=NegotiationStatus.PENDING
        )
        
        response = carrier.respond_to_offer(
            warehouse_offer, order, world,
            negotiation.current_round, negotiation.max_rounds
        )
        negotiation.responses.append(response)
        
        if response.status == NegotiationStatus.ACCEPTED:
            negotiation.is_complete = True
            negotiation.final_status = NegotiationStatus.ACCEPTED
            negotiation.agreed_price = offer_price
            negotiation.agreed_eta = response.counter_eta
            state.messages.append(f"Carrier ACCEPTS ${offer_price:.2f}")
        elif response.status == NegotiationStatus.REJECTED:
            negotiation.is_complete = True
            negotiation.final_status = NegotiationStatus.REJECTED
            state.messages.append("Carrier REJECTS - negotiation failed")
        else:
            state.messages.append(f"Carrier counters: ${response.counter_price:.2f}")
            negotiation.current_round += 1
        
        state.current_speaker = AgentType.WAREHOUSE
        state.negotiation = negotiation
        return state
    
    # Node: Check if negotiation should continue
    def should_continue(state: GraphState) -> Literal["warehouse", "carrier", "end"]:
        """Determine next step in workflow."""
        negotiation = state.negotiation
        
        if negotiation.is_complete:
            return "end"
        
        if negotiation.current_round > negotiation.max_rounds:
            negotiation.is_complete = True
            negotiation.final_status = NegotiationStatus.EXPIRED
            return "end"
        
        if state.current_speaker == AgentType.WAREHOUSE:
            return "warehouse"
        else:
            return "carrier"
    
    # Build the graph
    workflow.add_node("warehouse", warehouse_node)
    workflow.add_node("carrier", carrier_node)
    
    workflow.add_conditional_edges(
        "warehouse",
        should_continue,
        {
            "warehouse": "warehouse",
            "carrier": "carrier",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "carrier",
        should_continue,
        {
            "warehouse": "warehouse",
            "carrier": "carrier",
            "end": END
        }
    )
    
    workflow.set_entry_point("warehouse")
    
    return workflow.compile()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    from world import WorldState
    
    # Create world
    world = WorldState()
    
    # Create agents
    warehouse = WarehouseAgent(
        agent_id="WH-CC-001",
        location="Corpus Christi",
        budget=5000.0
    )
    
    carrier = CarrierAgent(
        agent_id="CR-TX-001",
        location="Houston",
        fleet_size=3
    )
    
    # Create test order
    order = Order(
        order_id="ORD-001",
        origin="Corpus Christi",
        destination="Houston",
        weight_kg=500,
        priority=OrderPriority.MEDIUM,
        max_budget=800.0,
        deadline_hours=24.0
    )
    
    # Test initial offer
    print("\n🧪 Testing Warehouse Initial Offer:")
    offer = warehouse.create_initial_offer(order, world, "NEG-001")
    print(f"   Offer: ${offer.offer_price:.2f}")
    
    # Test carrier response
    print("\n🧪 Testing Carrier Response:")
    response = carrier.respond_to_offer(offer, order, world, 1, 5)
    print(f"   Response: {response.status.value} - ${response.counter_price or offer.offer_price:.2f}")
