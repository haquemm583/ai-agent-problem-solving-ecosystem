"""
Deal History Database Module
SQLite database for persisting agent deal history and reputation scores.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from schema import DealHistory, ReputationScore, AgentType, DealOutcome


# Database file path
DB_PATH = Path(__file__).parent / "deal_history.db"


def init_database():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create deal_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deal_history (
            deal_id TEXT PRIMARY KEY,
            negotiation_id TEXT NOT NULL,
            warehouse_id TEXT NOT NULL,
            carrier_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            agreed_price REAL NOT NULL,
            negotiation_rounds INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            on_time_delivery INTEGER,
            actual_eta REAL,
            promised_eta REAL NOT NULL,
            timestamp TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    
    # Create reputation_scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_scores (
            agent_id TEXT PRIMARY KEY,
            agent_type TEXT NOT NULL,
            total_deals INTEGER DEFAULT 0,
            successful_deals INTEGER DEFAULT 0,
            failed_deals INTEGER DEFAULT 0,
            overall_score REAL DEFAULT 1.0,
            reliability_score REAL DEFAULT 1.0,
            negotiation_fairness REAL DEFAULT 1.0,
            avg_negotiation_rounds REAL DEFAULT 3.0,
            on_time_percentage REAL DEFAULT 1.0,
            last_updated TEXT NOT NULL
        )
    """)
    
    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_warehouse_deals 
        ON deal_history(warehouse_id, timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_carrier_deals 
        ON deal_history(carrier_id, timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_deal_outcome 
        ON deal_history(outcome, timestamp)
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


def save_deal_history(deal: DealHistory) -> bool:
    """
    Save a deal history record to the database.
    
    Args:
        deal: DealHistory object to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO deal_history (
                deal_id, negotiation_id, warehouse_id, carrier_id, order_id,
                agreed_price, negotiation_rounds, outcome, on_time_delivery,
                actual_eta, promised_eta, timestamp, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deal.deal_id,
            deal.negotiation_id,
            deal.warehouse_id,
            deal.carrier_id,
            deal.order_id,
            deal.agreed_price,
            deal.negotiation_rounds,
            deal.outcome.value,
            deal.on_time_delivery,
            deal.actual_eta,
            deal.promised_eta,
            deal.timestamp.isoformat(),
            deal.completed_at.isoformat() if deal.completed_at else None
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error saving deal history: {e}")
        return False


def load_deal_history(
    agent_id: Optional[str] = None,
    limit: int = 100,
    outcome_filter: Optional[DealOutcome] = None
) -> List[DealHistory]:
    """
    Load deal history from the database.
    
    Args:
        agent_id: Filter by specific agent (warehouse or carrier)
        limit: Maximum number of records to return
        outcome_filter: Filter by deal outcome
        
    Returns:
        List of DealHistory objects
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM deal_history WHERE 1=1"
        params = []
        
        if agent_id:
            query += " AND (warehouse_id = ? OR carrier_id = ?)"
            params.extend([agent_id, agent_id])
        
        if outcome_filter:
            query += " AND outcome = ?"
            params.append(outcome_filter.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to DealHistory objects
        deals = []
        for row in rows:
            deal = DealHistory(
                deal_id=row[0],
                negotiation_id=row[1],
                warehouse_id=row[2],
                carrier_id=row[3],
                order_id=row[4],
                agreed_price=row[5],
                negotiation_rounds=row[6],
                outcome=DealOutcome(row[7]),
                on_time_delivery=bool(row[8]) if row[8] is not None else None,
                actual_eta=row[9],
                promised_eta=row[10],
                timestamp=datetime.fromisoformat(row[11]),
                completed_at=datetime.fromisoformat(row[12]) if row[12] else None
            )
            deals.append(deal)
        
        return deals
        
    except Exception as e:
        print(f"❌ Error loading deal history: {e}")
        return []


def get_agent_deal_history(
    agent_id: str,
    limit: int = 50
) -> List[DealHistory]:
    """
    Get deal history for a specific agent.
    
    Args:
        agent_id: The agent's ID (warehouse or carrier)
        limit: Maximum number of records to return
        
    Returns:
        List of DealHistory objects involving this agent
    """
    return load_deal_history(agent_id=agent_id, limit=limit)


def save_reputation_score(reputation: ReputationScore) -> bool:
    """
    Save or update an agent's reputation score.
    
    Args:
        reputation: ReputationScore object to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO reputation_scores (
                agent_id, agent_type, total_deals, successful_deals, failed_deals,
                overall_score, reliability_score, negotiation_fairness,
                avg_negotiation_rounds, on_time_percentage, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reputation.agent_id,
            reputation.agent_type.value,
            reputation.total_deals,
            reputation.successful_deals,
            reputation.failed_deals,
            reputation.overall_score,
            reputation.reliability_score,
            reputation.negotiation_fairness,
            reputation.avg_negotiation_rounds,
            reputation.on_time_percentage,
            reputation.last_updated.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error saving reputation score: {e}")
        return False


def load_reputation_score(agent_id: str) -> Optional[ReputationScore]:
    """
    Load an agent's reputation score from the database.
    
    Args:
        agent_id: The agent's ID
        
    Returns:
        ReputationScore object or None if not found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reputation_scores WHERE agent_id = ?
        """, (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ReputationScore(
                agent_id=row[0],
                agent_type=AgentType(row[1]),
                total_deals=row[2],
                successful_deals=row[3],
                failed_deals=row[4],
                overall_score=row[5],
                reliability_score=row[6],
                negotiation_fairness=row[7],
                avg_negotiation_rounds=row[8],
                on_time_percentage=row[9],
                last_updated=datetime.fromisoformat(row[10])
            )
        
        return None
        
    except Exception as e:
        print(f"❌ Error loading reputation score: {e}")
        return None


def update_reputation_from_deal(deal: DealHistory) -> bool:
    """
    Update reputation scores for both agents involved in a deal.
    
    Args:
        deal: The completed deal
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Update warehouse reputation
        warehouse_rep = load_reputation_score(deal.warehouse_id)
        if warehouse_rep is None:
            warehouse_rep = ReputationScore(
                agent_id=deal.warehouse_id,
                agent_type=AgentType.WAREHOUSE
            )
        
        # Update carrier reputation
        carrier_rep = load_reputation_score(deal.carrier_id)
        if carrier_rep is None:
            carrier_rep = ReputationScore(
                agent_id=deal.carrier_id,
                agent_type=AgentType.CARRIER
            )
        
        # Update statistics for both agents
        for rep in [warehouse_rep, carrier_rep]:
            rep.total_deals += 1
            
            if deal.outcome == DealOutcome.SUCCESS:
                rep.successful_deals += 1
            elif deal.outcome == DealOutcome.FAILED:
                rep.failed_deals += 1
            
            # Calculate on-time delivery (primarily for carriers)
            if deal.on_time_delivery is not None and rep.agent_type == AgentType.CARRIER:
                # Update running average
                current_total = rep.on_time_percentage * (rep.total_deals - 1)
                new_value = 1.0 if deal.on_time_delivery else 0.0
                rep.on_time_percentage = (current_total + new_value) / rep.total_deals
                rep.reliability_score = rep.on_time_percentage
            
            # Update average negotiation rounds
            current_total = rep.avg_negotiation_rounds * (rep.total_deals - 1)
            rep.avg_negotiation_rounds = (current_total + deal.negotiation_rounds) / rep.total_deals
            
            # Calculate negotiation fairness (fewer rounds = better)
            # Normalize: 1-3 rounds = 1.0, 4-6 rounds = 0.75, 7+ rounds = 0.5
            if rep.avg_negotiation_rounds <= 3:
                rep.negotiation_fairness = 1.0
            elif rep.avg_negotiation_rounds <= 6:
                rep.negotiation_fairness = 0.75
            else:
                rep.negotiation_fairness = 0.5
            
            # Calculate overall score
            success_rate = rep.successful_deals / rep.total_deals if rep.total_deals > 0 else 1.0
            rep.overall_score = (
                success_rate * 0.5 +
                rep.reliability_score * 0.3 +
                rep.negotiation_fairness * 0.2
            )
            
            rep.last_updated = datetime.now()
        
        # Save updated reputations
        save_reputation_score(warehouse_rep)
        save_reputation_score(carrier_rep)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating reputation from deal: {e}")
        return False


def get_top_agents(
    agent_type: AgentType,
    limit: int = 10,
    metric: str = "overall_score"
) -> List[Dict[str, Any]]:
    """
    Get top-performing agents by reputation metric.
    
    Args:
        agent_type: Type of agents to rank
        limit: Number of agents to return
        metric: Metric to sort by (overall_score, reliability_score, etc.)
        
    Returns:
        List of dictionaries with agent_id and scores
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = f"""
            SELECT agent_id, overall_score, reliability_score, 
                   negotiation_fairness, total_deals
            FROM reputation_scores
            WHERE agent_type = ?
            ORDER BY {metric} DESC
            LIMIT ?
        """
        
        cursor.execute(query, (agent_type.value, limit))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "agent_id": row[0],
                "overall_score": row[1],
                "reliability_score": row[2],
                "negotiation_fairness": row[3],
                "total_deals": row[4]
            })
        
        return results
        
    except Exception as e:
        print(f"❌ Error getting top agents: {e}")
        return []


def get_deal_statistics(agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get aggregate statistics about deals.
    
    Args:
        agent_id: Optional agent ID to filter statistics
        
    Returns:
        Dictionary with statistics
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if agent_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                    AVG(negotiation_rounds) as avg_rounds,
                    AVG(agreed_price) as avg_price,
                    SUM(CASE WHEN on_time_delivery = 1 THEN 1 ELSE 0 END) as on_time,
                    COUNT(CASE WHEN on_time_delivery IS NOT NULL THEN 1 END) as completed
                FROM deal_history
                WHERE warehouse_id = ? OR carrier_id = ?
            """, (agent_id, agent_id))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                    AVG(negotiation_rounds) as avg_rounds,
                    AVG(agreed_price) as avg_price,
                    SUM(CASE WHEN on_time_delivery = 1 THEN 1 ELSE 0 END) as on_time,
                    COUNT(CASE WHEN on_time_delivery IS NOT NULL THEN 1 END) as completed
                FROM deal_history
            """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total = row[0] or 0
            completed = row[5] or 0
            return {
                "total_deals": total,
                "successful_deals": row[1] or 0,
                "avg_negotiation_rounds": round(row[2], 2) if row[2] else 0,
                "avg_agreed_price": round(row[3], 2) if row[3] else 0,
                "on_time_deliveries": row[4] or 0,
                "on_time_percentage": round((row[4] / completed * 100), 1) if completed > 0 else 0
            }
        
        return {
            "total_deals": 0,
            "successful_deals": 0,
            "avg_negotiation_rounds": 0,
            "avg_agreed_price": 0,
            "on_time_deliveries": 0,
            "on_time_percentage": 0
        }
        
    except Exception as e:
        print(f"❌ Error getting deal statistics: {e}")
        return {}


# Initialize database on module import
init_database()
