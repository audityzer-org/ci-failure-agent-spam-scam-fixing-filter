"""Logging Pipeline: Tracks and persists proposal data for ML ranking."""
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ProposalSource(Enum):
    """Source of proposal (CI failure or spam/scam)."""
    CI_FAILURE = "ci_failure"
    SPAM_SCAM = "spam_scam"

@dataclass
class ProposalLogEntry:
    """Single proposal log entry for ML training data."""
    timestamp: str
    proposal_id: str
    source: ProposalSource
    proposal_type: str
    user_action: Optional[str]
    user_feedback: Optional[str]
    selected_option: Optional[int]
    confidence_score: float
    risk_score: float
    context_data: Dict[str, Any]

class ProposalLogger:
    """Manages logging of proposals and user interactions."""
    
    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage = storage_backend
        self.entries: List[ProposalLogEntry] = []
    
    def log_proposal(self, proposal: Dict[str, Any], source: ProposalSource, context: Optional[Dict[str, Any]] = None) -> str:
        """Log a proposal event."""
        proposal_id = self._generate_id()
        timestamp = datetime.utcnow().isoformat()
        
        entry = ProposalLogEntry(
            timestamp=timestamp,
            proposal_id=proposal_id,
            source=source,
            proposal_type=proposal.get("type", "unknown"),
            user_action=None,
            user_feedback=None,
            selected_option=None,
            confidence_score=proposal.get("confidence_score", 0.5),
            risk_score=proposal.get("risk_score", 0.5),
            context_data=context or {}
        )
        
        self.entries.append(entry)
        if self.storage:
            self.storage.save(entry)
        
        logger.info(f"Logged proposal {proposal_id} from {source.value}")
        return proposal_id
    
    def log_user_action(self, proposal_id: str, action: str, feedback: Optional[str] = None, selected_option: Optional[int] = None):
        """Log user interaction with a proposal."""
        for entry in self.entries:
            if entry.proposal_id == proposal_id:
                entry.user_action = action
                entry.user_feedback = feedback
                entry.selected_option = selected_option
                
                if self.storage:
                    self.storage.update(entry)
                
                logger.info(f"Updated proposal {proposal_id} with action: {action}")
                return
        
        logger.warning(f"Proposal {proposal_id} not found")
    
    def export_training_data(self) -> List[Dict[str, Any]]:
        """Export all logged data for ML training."""
        return [asdict(entry) for entry in self.entries]
    
    def _generate_id(self) -> str:
        """Generate unique proposal ID."""
        import uuid
        return str(uuid.uuid4())[:8]

class PostgreSQLStorageBackend:
    """PostgreSQL backend for persistent storage of proposals."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
    
    def connect(self):
        """Initialize database connection."""
        # This would use psycopg2 or asyncpg in production
        # For now, this is a placeholder
        logger.info(f"Connecting to PostgreSQL: {self.connection_string}")
    
    def create_tables(self):
        """Create required database tables."""
        sql_proposals = """
        CREATE TABLE IF NOT EXISTS proposals (
            id SERIAL PRIMARY KEY,
            proposal_id VARCHAR(255) UNIQUE,
            source VARCHAR(50),
            proposal_type VARCHAR(100),
            timestamp TIMESTAMP,
            confidence_score FLOAT,
            risk_score FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        sql_user_actions = """
        CREATE TABLE IF NOT EXISTS user_actions (
            id SERIAL PRIMARY KEY,
            proposal_id VARCHAR(255),
            user_action VARCHAR(50),
            user_feedback TEXT,
            selected_option INT,
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
        );
        """
        
        logger.info("Database tables schema ready")
    
    def save(self, entry: ProposalLogEntry):
        """Save proposal entry to database."""
        logger.info(f"Saving proposal {entry.proposal_id} to database")
    
    def update(self, entry: ProposalLogEntry):
        """Update proposal entry in database."""
        logger.info(f"Updating proposal {entry.proposal_id} in database")
    
    def query_training_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Query proposals for ML training."""
        logger.info(f"Querying {limit} training records")
        return []

class MLRankingFeeder:
    """Feeds logged proposal data to ML ranking service."""
    
    def __init__(self, ml_service_url: str):
        self.ml_service_url = ml_service_url
    
    def send_training_batch(self, entries: List[Dict[str, Any]]):
        """Send batch of training data to ML ranking service."""
        logger.info(f"Sending {len(entries)} entries to ML ranking service")
        # In production, this would use requests or httpx to send data
    
    def get_ranked_proposals(self, proposal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get ML-ranked proposals for given incident."""
        logger.info("Fetching ML-ranked proposals")
        return []
