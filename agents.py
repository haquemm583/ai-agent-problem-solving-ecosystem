"""
Agent Logic and Prompts for MA-GET
Warehouse and Carrier agents with LangGraph integration.
"""

import uuid
import logging
import os
from typing import Dict, Any, Optional, Literal, List
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
    GraphState, Order, OrderPriority, ReputationScore, DealHistory, DealOutcome,
    CarrierPersona
)
from world import WorldState, calculate_fair_price_range, calculate_shipping_cost
import deal_database as db

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
    
    def get_deal_history(self, limit: int = 50) -> List[DealHistory]:
        """Get this agent's deal history from the database."""
        return db.get_agent_deal_history(self.agent_id, limit=limit)
    
    def get_reputation(self) -> ReputationScore:
        """Get this agent's current reputation score."""
        rep = db.load_reputation_score(self.agent_id)
        if rep is None:
            # Create default reputation if not found
            rep = ReputationScore(
                agent_id=self.agent_id,
                agent_type=self.agent_type
            )
            db.save_reputation_score(rep)
        return rep
    
    def update_reputation(self, reputation: ReputationScore):
        """Update this agent's reputation in the database."""
        db.save_reputation_score(reputation)
    
    def record_deal(self, deal: DealHistory):
        """Record a completed deal and update reputation."""
        # Save the deal to database
        db.save_deal_history(deal)
        
        # Update reputation scores for all involved agents
        db.update_reputation_from_deal(deal)
        
        # Refresh local reputation
        updated_rep = db.load_reputation_score(self.agent_id)
        if updated_rep and hasattr(self, 'state'):
            self.state.reputation = updated_rep
    
    def get_partner_reputation(self, partner_id: str) -> Optional[ReputationScore]:
        """Get the reputation of a potential negotiation partner."""
        return db.load_reputation_score(partner_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about this agent's deal history."""
        return db.get_deal_statistics(agent_id=self.agent_id)


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
        
        # Load reputation from database or create new
        reputation = db.load_reputation_score(agent_id)
        if reputation is None:
            reputation = ReputationScore(
                agent_id=agent_id,
                agent_type=AgentType.WAREHOUSE
            )
            db.save_reputation_score(reputation)
        
        self.state = WarehouseState(
            agent_id=agent_id,
            location=location,
            budget_remaining=budget,
            urgency_threshold=urgency_threshold,
            reputation=reputation
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
    
    def evaluate_carrier_reputation(self, carrier_id: str) -> Dict[str, Any]:
        """
        Evaluate a carrier's reputation and past performance.
        
        Args:
            carrier_id: The carrier's ID
            
        Returns:
            Dictionary with reputation analysis
        """
        carrier_rep = self.get_partner_reputation(carrier_id)
        
        if carrier_rep is None:
            return {
                "carrier_id": carrier_id,
                "reputation_found": False,
                "recommendation": "NEUTRAL",
                "reasoning": "No past history with this carrier. Proceed with standard caution."
            }
        
        # Analyze reputation
        score = carrier_rep.overall_score
        reliability = carrier_rep.reliability_score
        total_deals = carrier_rep.total_deals
        
        # Determine recommendation
        if score >= 0.8 and reliability >= 0.85:
            recommendation = "HIGHLY_RECOMMENDED"
            reasoning = (
                f"Excellent reputation (score: {score:.2f}, reliability: {reliability:.2f}). "
                f"Based on {total_deals} deals. Can trust for important shipments."
            )
        elif score >= 0.6 and reliability >= 0.7:
            recommendation = "RECOMMENDED"
            reasoning = (
                f"Good reputation (score: {score:.2f}, reliability: {reliability:.2f}). "
                f"Based on {total_deals} deals. Suitable for most shipments."
            )
        elif score >= 0.4:
            recommendation = "CAUTION"
            reasoning = (
                f"Mixed reputation (score: {score:.2f}, reliability: {reliability:.2f}). "
                f"Based on {total_deals} deals. Negotiate carefully and monitor closely."
            )
        else:
            recommendation = "AVOID"
            reasoning = (
                f"Poor reputation (score: {score:.2f}, reliability: {reliability:.2f}). "
                f"Based on {total_deals} deals. Consider alternative carriers."
            )
        
        return {
            "carrier_id": carrier_id,
            "reputation_found": True,
            "overall_score": score,
            "reliability_score": reliability,
            "total_deals": total_deals,
            "on_time_percentage": carrier_rep.on_time_percentage,
            "recommendation": recommendation,
            "reasoning": reasoning
        }
    
    def evaluate_bids(
        self,
        bids: List[NegotiationOffer],
        order: Order,
        world: WorldState,
        price_weight: float = 0.5,
        time_weight: float = 0.3,
        reputation_weight: float = 0.2
    ) -> Dict[str, Any]:
        """
        Evaluate multiple bids from different carriers and select the best one.
        
        Args:
            bids: List of bids from carriers
            order: The order being bid on
            world: Current world state
            price_weight: Weight for price in scoring (0-1)
            time_weight: Weight for ETA in scoring (0-1)
            reputation_weight: Weight for reputation in scoring (0-1)
            
        Returns:
            Dictionary with winner_id, winning_bid, scores, and reasoning
        """
        if not bids:
            return {
                "winner_id": None,
                "winning_bid": None,
                "scores": {},
                "reasoning": "No bids received"
            }
        
        # Normalize weights
        total_weight = price_weight + time_weight + reputation_weight
        price_weight /= total_weight
        time_weight /= total_weight
        reputation_weight /= total_weight
        
        # Calculate scores for each bid
        bid_scores = {}
        bid_details = {}
        
        # Find min/max for normalization
        prices = [bid.offer_price for bid in bids]
        etas = [bid.eta_estimate for bid in bids]
        min_price, max_price = min(prices), max(prices)
        min_eta, max_eta = min(etas), max(etas)
        
        for bid in bids:
            carrier_id = bid.sender_id
            
            # Price score (lower is better, so invert)
            if max_price > min_price:
                price_score = 1.0 - (bid.offer_price - min_price) / (max_price - min_price)
            else:
                price_score = 1.0
            
            # Time score (lower is better, so invert)
            if max_eta > min_eta:
                time_score = 1.0 - (bid.eta_estimate - min_eta) / (max_eta - min_eta)
            else:
                time_score = 1.0
            
            # Reputation score
            carrier_rep = self.get_partner_reputation(carrier_id)
            if carrier_rep:
                reputation_score = (carrier_rep.overall_score + carrier_rep.reliability_score) / 2.0
            else:
                reputation_score = 0.5  # Neutral for unknown carriers
            
            # Combined weighted score
            total_score = (
                price_weight * price_score +
                time_weight * time_score +
                reputation_weight * reputation_score
            )
            
            bid_scores[carrier_id] = total_score
            bid_details[carrier_id] = {
                "bid": bid,
                "price_score": price_score,
                "time_score": time_score,
                "reputation_score": reputation_score,
                "total_score": total_score
            }
        
        # Find the winner
        winner_id = max(bid_scores, key=bid_scores.get)
        winning_bid = bid_details[winner_id]["bid"]
        
        # Generate reasoning using LLM or rule-based
        if self.use_llm and self.llm:
            # Create a detailed prompt for LLM decision reasoning
            bid_summary = "\n".join([
                f"  - {details['bid'].sender_id}: ${details['bid'].offer_price:.2f}, "
                f"ETA {details['bid'].eta_estimate:.1f}h, "
                f"Score: {details['total_score']:.3f} "
                f"(Price: {details['price_score']:.2f}, Time: {details['time_score']:.2f}, Rep: {details['reputation_score']:.2f})"
                for details in bid_details.values()
            ])
            
            prompt = f"""You are a warehouse logistics manager evaluating bids from carriers.

ORDER DETAILS:
- Order: {order.order_id}
- Route: {order.origin} → {order.destination}
- Weight: {order.weight_kg}kg
- Priority: {order.priority.value}
- Max Budget: ${order.max_budget:.2f}

EVALUATION WEIGHTS:
- Price: {price_weight:.0%}
- Time: {time_weight:.0%}
- Reputation: {reputation_weight:.0%}

BIDS RECEIVED:
{bid_summary}

WINNER: {winner_id} with score {bid_scores[winner_id]:.3f}
- Price: ${winning_bid.offer_price:.2f}
- ETA: {winning_bid.eta_estimate:.1f} hours
- Carrier Reasoning: {winning_bid.reasoning}

Explain in 2-3 sentences why you selected this carrier over the others. Be specific about the tradeoffs."""
            
            try:
                response = self.llm.invoke(prompt)
                reasoning = response.content.strip()
            except Exception as e:
                reasoning = self._generate_rule_based_reasoning(
                    winner_id, winning_bid, bid_details, price_weight, time_weight, reputation_weight
                )
        else:
            reasoning = self._generate_rule_based_reasoning(
                winner_id, winning_bid, bid_details, price_weight, time_weight, reputation_weight
            )
        
        self.logger.monologue(
            context=f"Evaluating {len(bids)} bids for Order {order.order_id}",
            reasoning=f"Bids analyzed with weights: Price {price_weight:.0%}, Time {time_weight:.0%}, Rep {reputation_weight:.0%}\n\n{reasoning}",
            decision=f"Selected {winner_id}: ${winning_bid.offer_price:.2f} @ {winning_bid.eta_estimate:.1f}h",
            confidence=0.85
        )
        
        return {
            "winner_id": winner_id,
            "winning_bid": winning_bid,
            "scores": bid_scores,
            "reasoning": reasoning,
            "bid_details": bid_details
        }
    
    def _generate_rule_based_reasoning(
        self,
        winner_id: str,
        winning_bid: NegotiationOffer,
        bid_details: Dict[str, Any],
        price_weight: float,
        time_weight: float,
        reputation_weight: float
    ) -> str:
        """Generate selection reasoning using rules."""
        winner_details = bid_details[winner_id]
        
        # Identify strongest factor
        scores = {
            "price": winner_details["price_score"],
            "time": winner_details["time_score"],
            "reputation": winner_details["reputation_score"]
        }
        best_factor = max(scores, key=scores.get)
        
        reasoning_parts = []
        reasoning_parts.append(
            f"Selected {winner_id} with overall score of {winner_details['total_score']:.3f}."
        )
        
        if best_factor == "price":
            reasoning_parts.append(
                f"This carrier offered the most competitive price of ${winning_bid.offer_price:.2f}, "
                f"which is crucial given our {price_weight:.0%} price weight."
            )
        elif best_factor == "time":
            reasoning_parts.append(
                f"This carrier offers the fastest delivery at {winning_bid.eta_estimate:.1f} hours, "
                f"which aligns with our {time_weight:.0%} time priority."
            )
        else:
            reasoning_parts.append(
                f"This carrier has a strong reputation (score: {scores['reputation']:.2f}), "
                f"providing reliability worth the {reputation_weight:.0%} weight we assign to trust."
            )
        
        # Add note about tradeoffs
        other_bids = [d for cid, d in bid_details.items() if cid != winner_id]
        if other_bids:
            reasoning_parts.append(
                f"While other carriers offered variations in price/time tradeoffs, "
                f"this bid provides the best overall value for our current priorities."
            )
        
        return " ".join(reasoning_parts)


class CarrierAgent(BaseAgent):
    """Carrier Agent: Manages fleet and maximizes profit."""
    
    def __init__(
        self,
        agent_id: str,
        location: str,
        llm: Optional[Any] = None,
        fleet_size: int = 5,
        profit_target: float = 2.5,
        use_llm: bool = True,
        persona: Optional[CarrierPersona] = None,
        company_name: Optional[str] = None
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
        
        # Load reputation from database or create new
        reputation = db.load_reputation_score(agent_id)
        if reputation is None:
            reputation = ReputationScore(
                agent_id=agent_id,
                agent_type=AgentType.CARRIER
            )
            db.save_reputation_score(reputation)
        
        # Apply persona-specific configurations
        persona_config = self._get_persona_config(persona)
        
        self.state = CarrierState(
            agent_id=agent_id,
            fleet_size=fleet_size,
            available_trucks=fleet_size,
            current_location=location,
            profit_target_per_mile=persona_config.get("profit_target", profit_target),
            fuel_cost_per_mile=persona_config.get("fuel_cost_per_mile", 0.50),
            reputation=reputation,
            persona=persona,
            company_name=company_name or persona_config.get("company_name", "Generic Carrier"),
            speed_priority=persona_config.get("speed_priority", 1.0),
            green_rating=persona_config.get("green_rating", 0.5)
        )
        self.use_llm = use_llm and llm is not None
    
    def _get_persona_config(self, persona: Optional[CarrierPersona]) -> Dict[str, Any]:
        """Get configuration based on carrier persona."""
        configs = {
            CarrierPersona.PREMIUM: {
                "company_name": "SwiftLogistics",
                "profit_target": 3.50,
                "fuel_cost_per_mile": 0.45,  # Better fuel efficiency
                "speed_priority": 1.8,
                "green_rating": 0.6
            },
            CarrierPersona.GREEN: {
                "company_name": "EcoFreight",
                "profit_target": 2.80,
                "fuel_cost_per_mile": 0.40,  # Excellent fuel efficiency
                "speed_priority": 0.9,
                "green_rating": 0.95
            },
            CarrierPersona.DISCOUNT: {
                "company_name": "BudgetTrucking",
                "profit_target": 1.80,
                "fuel_cost_per_mile": 0.65,  # Older fleet, higher fuel cost
                "speed_priority": 0.7,
                "green_rating": 0.3
            }
        }
        
        if persona and persona in configs:
            return configs[persona]
        
        # Default configuration
        return {
            "company_name": "Generic Carrier",
            "profit_target": 2.5,
            "fuel_cost_per_mile": 0.50,
            "speed_priority": 1.0,
            "green_rating": 0.5
        }
    
    def create_initial_bid(
        self,
        order: Order,
        world: WorldState,
        auction_id: str
    ) -> NegotiationOffer:
        """
        Create an initial bid for an auction.
        
        Args:
            order: The order being bid on
            world: Current world state
            auction_id: The marketplace auction ID
            
        Returns:
            NegotiationOffer with the carrier's bid
        """
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
        
        # Calculate base costs
        fuel_cost = distance * self.state.fuel_cost_per_mile * fuel_mult
        base_price = distance * self.state.profit_target_per_mile * fuel_mult
        
        # Apply persona-specific adjustments
        if self.state.persona == CarrierPersona.PREMIUM:
            # Premium carriers charge more but promise faster delivery
            bid_price = base_price * 1.15
            eta = world.estimate_travel_time(order.origin, order.destination) * 0.85
            reasoning = (
                f"SwiftLogistics premium bid: ${bid_price:.2f}\n"
                f"Our fleet prioritizes speed with guaranteed expedited delivery.\n"
                f"Estimated delivery: {eta:.1f} hours (15% faster than standard).\n"
                f"Premium service includes real-time tracking and priority routing."
            )
        elif self.state.persona == CarrierPersona.GREEN:
            # Green carriers charge mid-range, emphasize sustainability
            bid_price = base_price * 1.08
            eta = world.estimate_travel_time(order.origin, order.destination) * 1.05
            reasoning = (
                f"EcoFreight sustainable bid: ${bid_price:.2f}\n"
                f"Our eco-friendly fleet uses optimized routes to minimize emissions.\n"
                f"Estimated delivery: {eta:.1f} hours with carbon-neutral shipping.\n"
                f"95% green rating with latest fuel-efficient technology."
            )
        elif self.state.persona == CarrierPersona.DISCOUNT:
            # Discount carriers offer lowest prices but slower
            bid_price = base_price * 0.92
            eta = world.estimate_travel_time(order.origin, order.destination) * 1.15
            reasoning = (
                f"BudgetTrucking competitive bid: ${bid_price:.2f}\n"
                f"We offer the most cost-effective solution for your shipping needs.\n"
                f"Estimated delivery: {eta:.1f} hours.\n"
                f"Reliable service at unbeatable prices."
            )
        else:
            # Default/generic carrier
            bid_price = base_price
            eta = world.estimate_travel_time(order.origin, order.destination)
            reasoning = (
                f"Standard bid: ${bid_price:.2f} for {distance:.0f} miles.\n"
                f"Estimated delivery: {eta:.1f} hours.\n"
                f"Competitive pricing with reliable service."
            )
        
        # Ensure bid doesn't exceed order max budget
        if bid_price > order.max_budget:
            bid_price = order.max_budget * 0.95
            reasoning += f"\n\nAdjusted to fit budget constraint of ${order.max_budget:.2f}."
        
        confidence = 0.8
        
        self.logger.monologue(
            context=f"Creating bid for Order {order.order_id} ({order.origin} → {order.destination})",
            reasoning=reasoning,
            decision=f"Bid: ${bid_price:.2f}, ETA: {eta:.1f}h",
            confidence=confidence
        )
        
        return NegotiationOffer(
            offer_id=f"BID-{uuid.uuid4().hex[:8]}",
            round_number=1,
            sender_id=self.agent_id,
            sender_type=AgentType.CARRIER,
            recipient_id="",  # Will be set by auction
            order_id=order.order_id,
            offer_price=bid_price,
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
                reputation_score=self.state.reputation.overall_score,
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
    
    def evaluate_warehouse_reputation(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Evaluate a warehouse's reputation and payment history.
        
        Args:
            warehouse_id: The warehouse's ID
            
        Returns:
            Dictionary with reputation analysis
        """
        warehouse_rep = self.get_partner_reputation(warehouse_id)
        
        if warehouse_rep is None:
            return {
                "warehouse_id": warehouse_id,
                "reputation_found": False,
                "recommendation": "NEUTRAL",
                "reasoning": "No past history with this warehouse. Proceed with standard terms."
            }
        
        # Analyze reputation
        score = warehouse_rep.overall_score
        fairness = warehouse_rep.negotiation_fairness
        total_deals = warehouse_rep.total_deals
        avg_rounds = warehouse_rep.avg_negotiation_rounds
        
        # Determine recommendation
        if score >= 0.8 and fairness >= 0.75:
            recommendation = "PREFERRED_CLIENT"
            reasoning = (
                f"Excellent reputation (score: {score:.2f}, fairness: {fairness:.2f}). "
                f"Based on {total_deals} deals, avg {avg_rounds:.1f} rounds. "
                f"Reliable partner - can offer competitive rates."
            )
        elif score >= 0.6 and fairness >= 0.5:
            recommendation = "GOOD_CLIENT"
            reasoning = (
                f"Good reputation (score: {score:.2f}, fairness: {fairness:.2f}). "
                f"Based on {total_deals} deals, avg {avg_rounds:.1f} rounds. "
                f"Standard negotiation approach recommended."
            )
        elif score >= 0.4:
            recommendation = "DIFFICULT_CLIENT"
            reasoning = (
                f"Mixed reputation (score: {score:.2f}, fairness: {fairness:.2f}). "
                f"Based on {total_deals} deals, avg {avg_rounds:.1f} rounds. "
                f"Expect tough negotiations - maintain firm pricing."
            )
        else:
            recommendation = "RISKY_CLIENT"
            reasoning = (
                f"Poor reputation (score: {score:.2f}, fairness: {fairness:.2f}). "
                f"Based on {total_deals} deals, avg {avg_rounds:.1f} rounds. "
                f"Require higher margins or avoid if alternatives exist."
            )
        
        return {
            "warehouse_id": warehouse_id,
            "reputation_found": True,
            "overall_score": score,
            "negotiation_fairness": fairness,
            "total_deals": total_deals,
            "avg_negotiation_rounds": avg_rounds,
            "recommendation": recommendation,
            "reasoning": reasoning
        }


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
# AUDITOR AGENT - Market Explainability and Transparency
# =============================================================================

class AuditorAgent(BaseAgent):
    """
    Auditor Agent: Analyzes market trends and provides explainability.
    
    This agent uses LLM to analyze deal history and generate insights about:
    - Which carriers are winning the most deals
    - Price trends and their causes (weather, demand, etc.)
    - Agent behavior patterns and fairness
    - Market health and recommendations
    """
    
    def __init__(
        self,
        agent_id: str = "AUDITOR-001",
        llm: Optional[Any] = None,
        use_llm: bool = True
    ):
        # Initialize LLM if not provided
        if llm is None and use_llm:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,  # Lower temperature for more analytical output
                api_key=os.getenv("OPENAI_API_KEY")
            )
        
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.ENVIRONMENTAL,  # Using ENVIRONMENTAL as closest type
            llm=llm
        )
        
        self.logger = AgentLogger(agent_id, AgentType.ENVIRONMENTAL)
    
    def generate_market_report(
        self,
        num_recent_deals: int = 50,
        world: Optional[WorldState] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive market analysis report using LLM.
        
        Args:
            num_recent_deals: Number of recent deals to analyze
            world: Optional WorldState for context on weather/routes
            
        Returns:
            Dictionary containing report sections and insights
        """
        self.logger.action("Generating Market Report", f"Analyzing last {num_recent_deals} deals")
        
        # Load recent deals from database
        all_deals = db.load_deal_history(limit=num_recent_deals)
        
        if not all_deals:
            return {
                "summary": "No deal history available for analysis.",
                "total_deals": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # Gather statistics
        stats = self._gather_market_statistics(all_deals)
        
        # Generate LLM-based insights
        insights = self._generate_llm_insights(all_deals, stats, world)
        
        # Compile report
        report = {
            "report_id": f"RPT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now().isoformat(),
            "analysis_period": {
                "total_deals": len(all_deals),
                "start_date": all_deals[-1].timestamp.isoformat() if all_deals else None,
                "end_date": all_deals[0].timestamp.isoformat() if all_deals else None
            },
            "statistics": stats,
            "insights": insights,
            "recommendations": self._generate_recommendations(stats, insights)
        }
        
        self.logger.monologue(
            context=f"Market Report Generated: {len(all_deals)} deals analyzed",
            reasoning=insights.get("market_health_reasoning", "Analysis complete"),
            decision=f"Generated report {report['report_id']}",
            confidence=0.85
        )
        
        return report
    
    def _gather_market_statistics(self, deals: List[DealHistory]) -> Dict[str, Any]:
        """Gather statistical data from deal history."""
        if not deals:
            return {}
        
        # Carrier performance
        carrier_stats = {}
        warehouse_stats = {}
        
        total_value = 0.0
        successful_deals = 0
        failed_deals = 0
        total_rounds = 0
        
        for deal in deals:
            # Carrier stats
            if deal.carrier_id not in carrier_stats:
                carrier_stats[deal.carrier_id] = {
                    "total_deals": 0,
                    "total_value": 0.0,
                    "successful": 0,
                    "failed": 0,
                    "avg_rounds": 0.0
                }
            
            carrier_stats[deal.carrier_id]["total_deals"] += 1
            carrier_stats[deal.carrier_id]["total_value"] += deal.agreed_price
            
            if deal.outcome == DealOutcome.SUCCESS:
                carrier_stats[deal.carrier_id]["successful"] += 1
                successful_deals += 1
            else:
                carrier_stats[deal.carrier_id]["failed"] += 1
                failed_deals += 1
            
            # Warehouse stats
            if deal.warehouse_id not in warehouse_stats:
                warehouse_stats[deal.warehouse_id] = {
                    "total_deals": 0,
                    "total_spent": 0.0,
                    "avg_price": 0.0
                }
            
            warehouse_stats[deal.warehouse_id]["total_deals"] += 1
            warehouse_stats[deal.warehouse_id]["total_spent"] += deal.agreed_price
            
            total_value += deal.agreed_price
            total_rounds += deal.negotiation_rounds
        
        # Calculate averages
        for carrier_id, stats in carrier_stats.items():
            if stats["total_deals"] > 0:
                stats["win_rate"] = stats["successful"] / stats["total_deals"]
                stats["avg_deal_value"] = stats["total_value"] / stats["total_deals"]
        
        for warehouse_id, stats in warehouse_stats.items():
            if stats["total_deals"] > 0:
                stats["avg_price"] = stats["total_spent"] / stats["total_deals"]
        
        # Price trend (last 10 vs previous)
        price_trend = "stable"
        if len(deals) >= 20:
            recent_avg = sum(d.agreed_price for d in deals[:10]) / 10
            previous_avg = sum(d.agreed_price for d in deals[10:20]) / 10
            change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
            
            if change_pct > 10:
                price_trend = "rising"
            elif change_pct < -10:
                price_trend = "falling"
        
        return {
            "total_deals_analyzed": len(deals),
            "total_market_value": total_value,
            "average_deal_value": total_value / len(deals) if deals else 0,
            "success_rate": successful_deals / len(deals) if deals else 0,
            "average_negotiation_rounds": total_rounds / len(deals) if deals else 0,
            "carrier_performance": carrier_stats,
            "warehouse_performance": warehouse_stats,
            "price_trend": price_trend,
            "market_competition": len(carrier_stats)
        }
    
    def _generate_llm_insights(
        self,
        deals: List[DealHistory],
        stats: Dict[str, Any],
        world: Optional[WorldState]
    ) -> Dict[str, str]:
        """Use LLM to generate insights from deal data."""
        
        # Prepare context for LLM
        carrier_summary = "\n".join([
            f"- {carrier_id}: {data['total_deals']} deals, "
            f"${data['avg_deal_value']:.2f} avg, "
            f"{data['win_rate']*100:.1f}% success rate"
            for carrier_id, data in stats.get("carrier_performance", {}).items()
        ])
        
        # Get weather context if available
        weather_context = ""
        if world:
            routes = world.get_all_routes()
            weather_summary = {}
            for route in routes:
                weather = route.weather_status.value
                weather_summary[weather] = weather_summary.get(weather, 0) + 1
            weather_context = ", ".join([f"{count} {weather}" for weather, count in weather_summary.items()])
        
        # Create LLM prompt
        prompt = f"""You are a Market Auditor analyzing a logistics marketplace. Generate insights from the following data:

MARKET STATISTICS:
- Total Deals: {stats.get('total_deals_analyzed', 0)}
- Total Value: ${stats.get('total_market_value', 0):.2f}
- Average Deal: ${stats.get('average_deal_value', 0):.2f}
- Success Rate: {stats.get('success_rate', 0)*100:.1f}%
- Avg Negotiation Rounds: {stats.get('average_negotiation_rounds', 0):.1f}
- Price Trend: {stats.get('price_trend', 'unknown')}
- Market Competition: {stats.get('market_competition', 0)} carriers

CARRIER PERFORMANCE:
{carrier_summary}

WEATHER CONDITIONS:
{weather_context if weather_context else "No weather data available"}

Provide insights on:
1. Which carrier is dominating and why
2. Are prices rising, falling, or stable? What might be causing this?
3. Is any agent acting unfairly or exploiting the system?
4. Overall market health assessment

Respond in JSON format:
{{
    "dominant_carrier": "<carrier_id and explanation>",
    "price_analysis": "<analysis of price trends and causes>",
    "fairness_assessment": "<assessment of agent behavior>",
    "market_health": "<HEALTHY|MODERATE|CONCERNING>",
    "market_health_reasoning": "<explanation>"
}}"""

        try:
            if self.llm:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                content = response.content
                
                # Try to parse JSON from response
                import json
                import re
                
                # Extract JSON from markdown code blocks if present
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                insights = json.loads(content)
                return insights
            else:
                # Fallback without LLM
                return self._generate_rule_based_insights(stats)
                
        except Exception as e:
            self.logger.logger.error(f"Error generating LLM insights: {e}")
            return self._generate_rule_based_insights(stats)
    
    def _generate_rule_based_insights(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """Generate insights using rule-based logic (fallback when LLM unavailable)."""
        carrier_perf = stats.get("carrier_performance", {})
        
        # Find dominant carrier
        dominant_carrier = "None"
        if carrier_perf:
            top_carrier = max(
                carrier_perf.items(),
                key=lambda x: x[1].get("total_deals", 0)
            )
            dominant_carrier = f"{top_carrier[0]} with {top_carrier[1]['total_deals']} deals"
        
        # Price analysis
        price_trend = stats.get("price_trend", "stable")
        price_analysis = f"Prices are {price_trend}. "
        if price_trend == "rising":
            price_analysis += "This may be due to increased demand or adverse weather conditions."
        elif price_trend == "falling":
            price_analysis += "This suggests increased competition or improved conditions."
        else:
            price_analysis += "Market appears stable with balanced supply and demand."
        
        # Market health
        success_rate = stats.get("success_rate", 0)
        if success_rate > 0.8:
            market_health = "HEALTHY"
            health_reason = "High success rate indicates efficient market operations"
        elif success_rate > 0.5:
            market_health = "MODERATE"
            health_reason = "Moderate success rate suggests some inefficiencies"
        else:
            market_health = "CONCERNING"
            health_reason = "Low success rate indicates market friction or misaligned expectations"
        
        return {
            "dominant_carrier": dominant_carrier,
            "price_analysis": price_analysis,
            "fairness_assessment": "No obvious exploitation detected in current data.",
            "market_health": market_health,
            "market_health_reasoning": health_reason
        }
    
    def _generate_recommendations(
        self,
        stats: Dict[str, Any],
        insights: Dict[str, str]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Market health recommendations
        market_health = insights.get("market_health", "MODERATE")
        if market_health == "CONCERNING":
            recommendations.append(
                "⚠️ Market health is concerning. Consider investigating failed negotiations "
                "and adjusting pricing models or carrier availability."
            )
        
        # Competition recommendations
        num_carriers = stats.get("market_competition", 0)
        if num_carriers < 3:
            recommendations.append(
                "📊 Low carrier competition detected. Consider onboarding more carriers "
                "to improve market efficiency and pricing."
            )
        
        # Price trend recommendations
        price_trend = stats.get("price_trend", "stable")
        if price_trend == "rising":
            recommendations.append(
                "📈 Prices are rising. Warehouses should consider increasing budgets or "
                "adjusting order timing to avoid peak demand periods."
            )
        elif price_trend == "falling":
            recommendations.append(
                "📉 Prices are falling. Good opportunity for warehouses to negotiate "
                "favorable long-term contracts."
            )
        
        # Negotiation efficiency
        avg_rounds = stats.get("average_negotiation_rounds", 0)
        if avg_rounds > 4:
            recommendations.append(
                "🔄 High average negotiation rounds suggest misaligned expectations. "
                "Consider calibrating initial offers closer to fair market rates."
            )
        
        if not recommendations:
            recommendations.append(
                "✅ Market is operating efficiently. Continue monitoring trends."
            )
        
        return recommendations
    
    def format_daily_briefing(self, report: Dict[str, Any]) -> str:
        """
        Format the market report as a human-readable daily briefing.
        
        Args:
            report: Market report dictionary from generate_market_report()
            
        Returns:
            Formatted string suitable for display
        """
        timestamp = datetime.fromisoformat(report["timestamp"])
        stats = report.get("statistics", {})
        insights = report.get("insights", {})
        recommendations = report.get("recommendations", [])
        
        briefing = f"""
╔══════════════════════════════════════════════════════════════════╗
║                   DAILY ECONOMIC BRIEFING                        ║
║                   Report ID: {report.get('report_id', 'N/A')}                      ║
║                   {timestamp.strftime('%Y-%m-%d %H:%M:%S')}                         ║
╚══════════════════════════════════════════════════════════════════╝

📊 MARKET OVERVIEW
────────────────────────────────────────────────────────────────────
• Total Deals Analyzed: {stats.get('total_deals_analyzed', 0)}
• Total Market Value: ${stats.get('total_market_value', 0):,.2f}
• Average Deal Value: ${stats.get('average_deal_value', 0):.2f}
• Market Success Rate: {stats.get('success_rate', 0)*100:.1f}%
• Avg Negotiation Rounds: {stats.get('average_negotiation_rounds', 0):.1f}
• Price Trend: {stats.get('price_trend', 'N/A').upper()}

🏆 CARRIER PERFORMANCE
────────────────────────────────────────────────────────────────────
"""
        
        # Add carrier details
        carrier_perf = stats.get('carrier_performance', {})
        for carrier_id, data in sorted(
            carrier_perf.items(),
            key=lambda x: x[1].get('total_deals', 0),
            reverse=True
        ):
            briefing += f"""
{carrier_id}:
  • Total Deals: {data.get('total_deals', 0)}
  • Win Rate: {data.get('win_rate', 0)*100:.1f}%
  • Avg Deal Value: ${data.get('avg_deal_value', 0):.2f}
"""
        
        briefing += f"""
🔍 MARKET INSIGHTS
────────────────────────────────────────────────────────────────────
• Dominant Player: {insights.get('dominant_carrier', 'N/A')}

• Price Analysis: {insights.get('price_analysis', 'N/A')}

• Fairness Assessment: {insights.get('fairness_assessment', 'N/A')}

• Market Health: {insights.get('market_health', 'N/A')}
  → {insights.get('market_health_reasoning', 'N/A')}

💡 RECOMMENDATIONS
────────────────────────────────────────────────────────────────────
"""
        
        for i, rec in enumerate(recommendations, 1):
            briefing += f"{i}. {rec}\n"
        
        briefing += """
════════════════════════════════════════════════════════════════════
"""
        
        return briefing


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
