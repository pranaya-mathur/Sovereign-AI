"""Audit store - Persistence layer for LLM observability.

Stores every LLM interaction with:
- Prompt and response
- Fired signals
- Verdict decision
- Action taken

Goals:
- Audit trail for compliance
- Dashboard data source
- Analytics and insights
- Monetization ready (usage tracking)
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict

from contracts.verdict import Verdict, VerdictSummary


class AuditStore:
    """SQLite-based persistence for LLM audit trail.
    
    Lightweight, embedded database suitable for:
    - Development and testing
    - Single-server deployments
    - Quick prototyping
    
    For production scale, migrate to PostgreSQL/TimescaleDB.
    """
    
    def __init__(self, db_path: str = "data/audit.db"):
        """Initialize audit store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database schema."""
        cursor = self.conn.cursor()
        
        # Main interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT UNIQUE NOT NULL,
                
                -- Request
                prompt TEXT NOT NULL,
                model TEXT,
                
                -- Response
                response TEXT,
                response_blocked BOOLEAN NOT NULL,
                
                -- Verdict
                verdict_id TEXT NOT NULL,
                verdict_severity TEXT NOT NULL,
                verdict_action TEXT NOT NULL,
                verdict_reason TEXT,
                verdict_confidence REAL,
                
                -- Failure
                failure_class TEXT,
                
                -- Metadata
                policy_version TEXT,
                timestamp DATETIME NOT NULL,
                
                -- JSON fields for complex data
                metadata_json TEXT,
                
                -- Indexes
                INDEX idx_timestamp (timestamp),
                INDEX idx_verdict_action (verdict_action),
                INDEX idx_verdict_severity (verdict_severity),
                INDEX idx_failure_class (failure_class)
            )
        """)
        
        # Signals table (one-to-many with interactions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fired_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT NOT NULL,
                
                signal_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation TEXT,
                timestamp DATETIME NOT NULL,
                
                metadata_json TEXT,
                
                FOREIGN KEY (interaction_id) REFERENCES llm_interactions(interaction_id),
                INDEX idx_interaction_id (interaction_id),
                INDEX idx_signal_name (signal_name)
            )
        """)
        
        self.conn.commit()
    
    def store_interaction(
        self,
        interaction_id: str,
        prompt: str,
        response: Optional[str],
        verdict: Verdict,
        model: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an LLM interaction with verdict.
        
        Args:
            interaction_id: Unique ID for this interaction
            prompt: User prompt/query
            response: LLM response (None if blocked)
            verdict: Verdict decision object
            model: Model name/identifier
            metadata: Additional context
        """
        cursor = self.conn.cursor()
        
        # Store main interaction
        cursor.execute("""
            INSERT INTO llm_interactions (
                interaction_id, prompt, model, response, response_blocked,
                verdict_id, verdict_severity, verdict_action, verdict_reason,
                verdict_confidence, failure_class, policy_version, timestamp,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction_id,
            prompt,
            model,
            response,
            verdict.should_block,
            verdict.verdict_id,
            verdict.severity.value,
            verdict.action.value,
            verdict.reason,
            verdict.confidence,
            verdict.failure_class.value if verdict.failure_class else None,
            verdict.policy_version,
            verdict.timestamp.isoformat(),
            json.dumps(metadata or {}),
        ))
        
        # Store fired signals
        for signal in verdict.fired_signals:
            cursor.execute("""
                INSERT INTO fired_signals (
                    interaction_id, signal_name, confidence,
                    explanation, timestamp, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                interaction_id,
                signal.signal_name,
                signal.confidence,
                signal.explanation,
                signal.timestamp.isoformat(),
                json.dumps(signal.metadata),
            ))
        
        self.conn.commit()
    
    def get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific interaction by ID."""
        cursor = self.conn.cursor()
        
        # Get main interaction
        cursor.execute(
            "SELECT * FROM llm_interactions WHERE interaction_id = ?",
            (interaction_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        interaction = dict(row)
        
        # Get fired signals
        cursor.execute(
            "SELECT * FROM fired_signals WHERE interaction_id = ?",
            (interaction_id,)
        )
        signals = [dict(r) for r in cursor.fetchall()]
        interaction["fired_signals"] = signals
        
        return interaction
    
    def get_recent_interactions(
        self,
        limit: int = 50,
        action_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent interactions, optionally filtered by action.
        
        Args:
            limit: Maximum number of results
            action_filter: Filter by action (block, warn, log, allow)
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM llm_interactions"
        params: List[Any] = []
        
        if action_filter:
            query += " WHERE verdict_action = ?"
            params.append(action_filter)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_blocked_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get interactions that were blocked."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM llm_interactions
            WHERE response_blocked = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_summary(
        self,
        since: Optional[datetime] = None,
    ) -> VerdictSummary:
        """Generate summary statistics.
        
        Args:
            since: Only include interactions after this timestamp
        """
        cursor = self.conn.cursor()
        
        # Base query
        query = "SELECT * FROM llm_interactions"
        params: List[Any] = []
        
        if since:
            query += " WHERE timestamp >= ?"
            params.append(since.isoformat())
        
        cursor.execute(query, params)
        interactions = cursor.fetchall()
        
        summary = VerdictSummary()
        
        for row in interactions:
            # Count totals
            summary.total_verdicts += 1
            
            # Count by action
            action = row["verdict_action"]
            if action == "block":
                summary.blocked_count += 1
            elif action == "warn":
                summary.warned_count += 1
            elif action == "allow":
                summary.allowed_count += 1
            
            # Count by severity
            severity = row["verdict_severity"]
            if severity == "critical":
                summary.critical_count += 1
            elif severity == "high":
                summary.high_count += 1
            elif severity == "medium":
                summary.medium_count += 1
            elif severity == "low":
                summary.low_count += 1
            
            # Count failure classes
            failure_class = row["failure_class"]
            if failure_class:
                summary.failure_class_counts[failure_class] = \
                    summary.failure_class_counts.get(failure_class, 0) + 1
        
        # Get signal counts
        query = "SELECT signal_name, COUNT(*) as count FROM fired_signals"
        if since:
            query += " WHERE timestamp >= ?"
        query += " GROUP BY signal_name ORDER BY count DESC"
        
        cursor.execute(query, params)
        for row in cursor.fetchall():
            summary.most_fired_signals[row["signal_name"]] = row["count"]
        
        return summary
    
    def get_signal_history(
        self,
        signal_name: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get history of a specific signal firing."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT fs.*, li.prompt, li.verdict_action
            FROM fired_signals fs
            JOIN llm_interactions li ON fs.interaction_id = li.interaction_id
            WHERE fs.signal_name = ?
            ORDER BY fs.timestamp DESC
            LIMIT ?
        """, (signal_name, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_failure_timeline(
        self,
        days: int = 7,
    ) -> Dict[str, List[int]]:
        """Get daily failure counts for the last N days.
        
        Returns:
            Dict mapping date strings to [total, blocked, warned] counts
        """
        cursor = self.conn.cursor()
        since = datetime.utcnow() - timedelta(days=days)
        
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total,
                SUM(CASE WHEN response_blocked = 1 THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN verdict_action = 'warn' THEN 1 ELSE 0 END) as warned
            FROM llm_interactions
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (since.isoformat(),))
        
        timeline = {}
        for row in cursor.fetchall():
            timeline[row["date"]] = [
                row["total"],
                row["blocked"],
                row["warned"],
            ]
        
        return timeline
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
