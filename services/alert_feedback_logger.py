"""Alert Feedback Logger for Platform Integration

Logs user feedback on alert recommendations and actions for ML training
and performance monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import asyncio
import aiofiles
import httpx

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback for alert actions."""
    ACTION_SHOWN = "action_shown"
    ACTION_ACCEPTED = "action_accepted"
    ACTION_REJECTED = "action_rejected"
    ACTION_IGNORED = "action_ignored"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_ESCALATED = "alert_escalated"


class AlertFeedbackLogger:
    """Logs alert feedback for ML training and monitoring."""

    def __init__(self, 
                 log_file: str = "/var/log/alert_feedback.log",
                 api_endpoint: Optional[str] = None,
                 batch_size: int = 100,
                 flush_interval: int = 30):
        self.log_file = log_file
        self.api_endpoint = api_endpoint
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.feedback_buffer = []
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup file logging for feedback."""
        try:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        except Exception as e:
            logger.error(f"Error setting up logging: {str(e)}")

    async def log_feedback(self,
                          feedback_type: FeedbackType,
                          alert_id: str,
                          action_id: str,
                          user_id: str,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log alert feedback event."""
        try:
            feedback_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "feedback_type": feedback_type.value,
                "alert_id": alert_id,
                "action_id": action_id,
                "user_id": user_id,
                "metadata": metadata or {}
            }

            # Add to buffer
            self.feedback_buffer.append(feedback_entry)
            self.logger.info(json.dumps(feedback_entry))

            # Flush if buffer is full
            if len(self.feedback_buffer) >= self.batch_size:
                await self.flush_buffer()

        except Exception as e:
            self.logger.error(f"Error logging feedback: {str(e)}")

    async def log_action_shown(self,
                               alert_id: str,
                               actions: list,
                               user_id: str) -> None:
        """Log when actions are shown to user."""
        await self.log_feedback(
            FeedbackType.ACTION_SHOWN,
            alert_id,
            ",".join([a.get('id', '') for a in actions]),
            user_id,
            {"actions_count": len(actions)}
        )

    async def log_action_outcome(self,
                                 alert_id: str,
                                 action_id: str,
                                 outcome: str,
                                 user_id: str,
                                 duration_ms: Optional[int] = None) -> None:
        """Log action execution outcome."""
        feedback_type = (
            FeedbackType.ACTION_EXECUTED if outcome == "success"
            else FeedbackType.ACTION_FAILED
        )
        
        metadata = {"outcome": outcome}
        if duration_ms:
            metadata["duration_ms"] = duration_ms

        await self.log_feedback(
            feedback_type,
            alert_id,
            action_id,
            user_id,
            metadata
        )

    async def log_user_decision(self,
                                alert_id: str,
                                action_id: str,
                                decision: str,
                                user_id: str,
                                reasoning: Optional[str] = None) -> None:
        """Log user decision on action recommendation."""
        decision_map = {
            "accept": FeedbackType.ACTION_ACCEPTED,
            "reject": FeedbackType.ACTION_REJECTED,
            "ignore": FeedbackType.ACTION_IGNORED
        }
        
        feedback_type = decision_map.get(
            decision, FeedbackType.ACTION_IGNORED
        )
        
        metadata = {"reasoning": reasoning} if reasoning else {}
        
        await self.log_feedback(
            feedback_type,
            alert_id,
            action_id,
            user_id,
            metadata
        )

    async def flush_buffer(self) -> None:
        """Flush feedback buffer to storage."""
        if not self.feedback_buffer:
            return

        try:
            if self.api_endpoint:
                await self._send_to_api()
            else:
                await self._save_to_file()
            
            self.feedback_buffer = []
            self.logger.info(f"Flushed {len(self.feedback_buffer)} feedback entries")
        except Exception as e:
            self.logger.error(f"Error flushing buffer: {str(e)}")

    async def _send_to_api(self) -> None:
        """Send feedback to remote API."""
        if not self.api_endpoint:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_endpoint}/feedback/batch",
                    json={"entries": self.feedback_buffer},
                    timeout=10.0
                )
                response.raise_for_status()
                self.logger.info(
                    f"Sent {len(self.feedback_buffer)} entries to API"
                )
        except Exception as e:
            self.logger.error(f"Error sending to API: {str(e)}")

    async def _save_to_file(self) -> None:
        """Save feedback to file."""
        try:
            async with aiofiles.open(self.log_file, 'a') as f:
                for entry in self.feedback_buffer:
                    await f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.error(f"Error saving to file: {str(e)}")

    async def start_periodic_flush(self) -> None:
        """Start periodic buffer flushing."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_buffer()
            except Exception as e:
                self.logger.error(f"Error in periodic flush: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback logging statistics."""
        return {
            "buffer_size": len(self.feedback_buffer),
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
            "api_endpoint": self.api_endpoint,
            "log_file": self.log_file
        }
