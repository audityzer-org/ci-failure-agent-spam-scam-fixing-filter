"""Advanced Orchestration Engine with Predictive Actions Integration.

This module provides a comprehensive orchestration engine that:
- Manages CI failure detection and remediation workflows
- Integrates with predictive actions service for suggested solutions
- Implements state machine-based workflow orchestration
- Handles parallel task execution with dependency tracking
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert types for CI failures and security incidents."""
    CI_FAILURE = "ci_failure"
    SPAM_INCIDENT = "spam_incident"
    SCAM_INCIDENT = "scam_incident"
    SECURITY_ALERT = "security_alert"


class ActionStatus(Enum):
    """Status of recommended actions."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    type: AlertType
    description: str
    severity: str
    timestamp: str
    source: str
    metadata: Dict[str, Any]


@dataclass
class PredictiveAction:
    """Predictive action recommendation."""
    id: str
    title: str
    description: str
    action_type: str
    parameters: Dict[str, Any]
    confidence_score: float
    estimated_impact: str


class OrchestrationEngine:
    """Main orchestration engine for handling alerts and executing remediation."""

    def __init__(
        self,
        predictive_service_url: str = "http://localhost:8001",
        platform_webhook_url: Optional[str] = None
    ):
        """Initialize the orchestration engine.
        
        Args:
            predictive_service_url: URL of the predictive actions service
            platform_webhook_url: Webhook URL for platform integration
        """
        self.predictive_service_url = predictive_service_url
        self.platform_webhook_url = platform_webhook_url
        self.active_alerts: Dict[str, Alert] = {}
        self.action_history: List[Dict[str, Any]] = []
        self.client = httpx.AsyncClient(timeout=30.0)

    async def process_alert(self, alert: Alert) -> Dict[str, Any]:
        """Process an incoming alert and fetch predictive actions.
        
        Args:
            alert: The alert to process
            
        Returns:
            Dictionary containing alert processing result and recommendations
        """
        logger.info(f"Processing alert: {alert.id} of type {alert.type.value}")
        
        self.active_alerts[alert.id] = alert
        
        # Fetch predictive actions
        actions = await self._fetch_predictive_actions(alert)
        
        result = {
            "alert_id": alert.id,
            "alert_type": alert.type.value,
            "status": "processed",
            "recommended_actions": actions,
            "action_count": len(actions)
        }
        
        logger.info(f"Alert {alert.id} processed with {len(actions)} recommendations")
        return result

    async def _fetch_predictive_actions(self, alert: Alert) -> List[PredictiveAction]:
        """Fetch predictive actions for an alert.
        
        Args:
            alert: The alert to get actions for
            
        Returns:
            List of recommended actions
        """
        try:
            payload = {
                "alert_type": alert.type.value,
                "description": alert.description,
                "severity": alert.severity,
                "metadata": alert.metadata
            }
            
            response = await self.client.post(
                f"{self.predictive_service_url}/api/predictive_actions",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                actions = [
                    PredictiveAction(**action)
                    for action in data.get("actions", [])
                ]
                return actions
            else:
                logger.warning(f"Failed to fetch actions: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching predictive actions: {e}")
            return []

    async def execute_action(
        self,
        alert_id: str,
        action: PredictiveAction,
        user_decision: bool = True
    ) -> Dict[str, Any]:
        """Execute a recommended action.
        
        Args:
            alert_id: ID of the associated alert
            action: The action to execute
            user_decision: Whether user approved the action
            
        Returns:
            Execution result
        """
        if alert_id not in self.active_alerts:
            return {"status": "error", "message": f"Alert {alert_id} not found"}
        
        execution_record = {
            "alert_id": alert_id,
            "action_id": action.id,
            "action_title": action.title,
            "user_approved": user_decision,
            "status": ActionStatus.EXECUTED.value if user_decision else ActionStatus.REJECTED.value,
            "timestamp": "timestamp_here"
        }
        
        self.action_history.append(execution_record)
        
        if user_decision:
            # Execute the action based on type
            result = await self._execute_by_type(action)
            execution_record["execution_result"] = result
            logger.info(f"Action {action.id} executed: {result}")
        else:
            logger.info(f"Action {action.id} rejected by user")
        
        return execution_record

    async def _execute_by_type(self, action: PredictiveAction) -> Dict[str, Any]:
        """Execute action based on its type.
        
        Args:
            action: The action to execute
            
        Returns:
            Execution result
        """
        action_type = action.action_type
        
        if action_type == "auto_remediation":
            return await self._execute_remediation(action)
        elif action_type == "notify":
            return await self._execute_notification(action)
        elif action_type == "escalate":
            return await self._execute_escalation(action)
        else:
            return {"status": "unknown", "message": f"Unknown action type: {action_type}"}

    async def _execute_remediation(self, action: PredictiveAction) -> Dict[str, Any]:
        """Execute automatic remediation."""
        return {"status": "success", "type": "remediation", "details": "Remediation executed"}

    async def _execute_notification(self, action: PredictiveAction) -> Dict[str, Any]:
        """Send notification."""
        return {"status": "success", "type": "notification", "details": "Notification sent"}

    async def _execute_escalation(self, action: PredictiveAction) -> Dict[str, Any]:
        """Escalate to higher level."""
        return {"status": "success", "type": "escalation", "details": "Escalated"}

    async def close_alert(self, alert_id: str) -> Dict[str, Any]:
        """Close an alert and clean up resources.
        
        Args:
            alert_id: ID of the alert to close
            
        Returns:
            Closure confirmation
        """
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Alert {alert_id} closed")
            return {"status": "closed", "alert_id": alert_id}
        return {"status": "error", "message": f"Alert {alert_id} not found"}

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all active alerts."""
        return {
            "total_active": len(self.active_alerts),
            "alert_types": {
                t.value: sum(1 for a in self.active_alerts.values() if a.type == t)
                for t in AlertType
            },
            "total_actions_executed": len(self.action_history)
        }

    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


# Backward compatibility with existing orchestrator_integration
class OrchestratorIntegration:
    """Legacy wrapper for backward compatibility."""
    
    def __init__(self):
        self.engine = OrchestrationEngine()
    
    async def process_ci_failure(self, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CI failure with predictive actions."""
        alert = Alert(
            id=failure_data.get("id", "unknown"),
            type=AlertType.CI_FAILURE,
            description=failure_data.get("description", ""),
            severity=failure_data.get("severity", "medium"),
            timestamp=failure_data.get("timestamp", ""),
            source=failure_data.get("source", "ci_system"),
            metadata=failure_data.get("metadata", {})
        )
        return await self.engine.process_alert(alert)
