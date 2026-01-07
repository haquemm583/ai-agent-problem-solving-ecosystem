"""
Shared Event Log System for MA-GET Dashboard
Enables real-time communication between simulation and Streamlit UI.
"""

import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue
import os


class EventType(str, Enum):
    """Types of events in the simulation."""
    SYSTEM = "SYSTEM"
    WORLD_UPDATE = "WORLD_UPDATE"
    AGENT_MONOLOGUE = "AGENT_MONOLOGUE"
    OFFER = "OFFER"
    RESPONSE = "RESPONSE"
    NEGOTIATION_START = "NEGOTIATION_START"
    NEGOTIATION_END = "NEGOTIATION_END"
    WEATHER_CHANGE = "WEATHER_CHANGE"
    ROUTE_UPDATE = "ROUTE_UPDATE"


@dataclass
class SimulationEvent:
    """A single event in the simulation."""
    event_type: EventType
    timestamp: datetime
    agent_id: Optional[str]
    agent_type: Optional[str]
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "title": self.title,
            "message": self.message,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimulationEvent":
        return cls(
            event_type=EventType(d["event_type"]),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            agent_id=d.get("agent_id"),
            agent_type=d.get("agent_type"),
            title=d["title"],
            message=d["message"],
            data=d.get("data", {})
        )


class EventLog:
    """
    Thread-safe event log for the simulation.
    Supports file-based persistence for Streamlit dashboard integration.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.events: List[SimulationEvent] = []
        self.subscribers: List[Callable[[SimulationEvent], None]] = []
        self.log_file = ".maget_events.json"
        self._file_lock = threading.Lock()
        self._initialized = True
    
    def log(
        self,
        event_type: EventType,
        title: str,
        message: str,
        agent_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> SimulationEvent:
        """Log a new event."""
        event = SimulationEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            agent_id=agent_id,
            agent_type=agent_type,
            title=title,
            message=message,
            data=data or {}
        )
        
        with self._lock:
            self.events.append(event)
            # Notify subscribers
            for subscriber in self.subscribers:
                try:
                    subscriber(event)
                except Exception:
                    pass
        
        # Persist to file for dashboard
        self._persist_event(event)
        
        return event
    
    def _persist_event(self, event: SimulationEvent):
        """Persist event to file for cross-process communication."""
        with self._file_lock:
            try:
                # Read existing events
                if os.path.exists(self.log_file):
                    with open(self.log_file, 'r') as f:
                        events_data = json.load(f)
                else:
                    events_data = []
                
                # Append new event
                events_data.append(event.to_dict())
                
                # Keep only last 500 events
                if len(events_data) > 500:
                    events_data = events_data[-500:]
                
                # Write back
                with open(self.log_file, 'w') as f:
                    json.dump(events_data, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not persist event: {e}")
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[SimulationEvent]:
        """Get events with optional filtering."""
        with self._lock:
            events = self.events.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        return events[-limit:]
    
    def clear(self):
        """Clear all events."""
        with self._lock:
            self.events.clear()
        
        with self._file_lock:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
    
    def subscribe(self, callback: Callable[[SimulationEvent], None]):
        """Subscribe to new events."""
        self.subscribers.append(callback)
    
    @classmethod
    def load_from_file(cls, filepath: str = ".maget_events.json") -> List[SimulationEvent]:
        """Load events from file (for dashboard)."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    events_data = json.load(f)
                return [SimulationEvent.from_dict(e) for e in events_data]
        except Exception as e:
            print(f"Warning: Could not load events: {e}")
        return []


# Global singleton instance
event_log = EventLog()


# Convenience functions
def log_system(title: str, message: str, data: Optional[Dict] = None):
    """Log a system event."""
    return event_log.log(EventType.SYSTEM, title, message, data=data)


def log_world_update(title: str, message: str, data: Optional[Dict] = None):
    """Log a world state update."""
    return event_log.log(EventType.WORLD_UPDATE, title, message, data=data)


def log_agent_monologue(
    agent_id: str,
    agent_type: str,
    context: str,
    reasoning: str,
    decision: str,
    confidence: float
):
    """Log an agent's internal monologue."""
    return event_log.log(
        EventType.AGENT_MONOLOGUE,
        f"{agent_type} Monologue",
        decision,
        agent_id=agent_id,
        agent_type=agent_type,
        data={
            "context": context,
            "reasoning": reasoning,
            "decision": decision,
            "confidence": confidence
        }
    )


def log_offer(
    agent_id: str,
    agent_type: str,
    offer_price: float,
    reasoning: str,
    order_id: str
):
    """Log a negotiation offer."""
    return event_log.log(
        EventType.OFFER,
        f"Offer: ${offer_price:.2f}",
        reasoning,
        agent_id=agent_id,
        agent_type=agent_type,
        data={
            "offer_price": offer_price,
            "order_id": order_id
        }
    )


def log_response(
    agent_id: str,
    agent_type: str,
    status: str,
    counter_price: Optional[float],
    reasoning: str
):
    """Log a negotiation response."""
    price_str = f"${counter_price:.2f}" if counter_price else "N/A"
    return event_log.log(
        EventType.RESPONSE,
        f"{status}: {price_str}",
        reasoning,
        agent_id=agent_id,
        agent_type=agent_type,
        data={
            "status": status,
            "counter_price": counter_price
        }
    )


def log_negotiation_start(
    negotiation_id: str,
    order_id: str,
    origin: str,
    destination: str,
    warehouse_id: str,
    carrier_id: str
):
    """Log negotiation start."""
    return event_log.log(
        EventType.NEGOTIATION_START,
        "Negotiation Started",
        f"Order {order_id}: {origin} → {destination}",
        data={
            "negotiation_id": negotiation_id,
            "order_id": order_id,
            "origin": origin,
            "destination": destination,
            "warehouse_id": warehouse_id,
            "carrier_id": carrier_id
        }
    )


def log_negotiation_end(
    negotiation_id: str,
    status: str,
    agreed_price: Optional[float],
    rounds: int
):
    """Log negotiation end."""
    price_str = f"${agreed_price:.2f}" if agreed_price else "No deal"
    return event_log.log(
        EventType.NEGOTIATION_END,
        f"Negotiation {status}",
        f"Final: {price_str} after {rounds} round(s)",
        data={
            "negotiation_id": negotiation_id,
            "status": status,
            "agreed_price": agreed_price,
            "rounds": rounds
        }
    )
