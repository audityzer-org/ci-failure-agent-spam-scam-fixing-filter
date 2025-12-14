"""Platform client for predictive actions integration.

Integrates with auditorsec-platform-poc to:
- Call /api/predictive_actions endpoint
- Display 2-3 action recommendations in UI
- Log user selections for ML model training
"""

import aiohttp
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ActionRecommendation:
    """Single action recommendation for UI display."""
    action_id: str
    title: str
    description: str
    action_type: str
    priority: int
    estimated_time: Optional[str] = None
    success_rate: Optional[float] = None
    selected: bool = False


@dataclass
class PredictiveActionsResponse:
    """Response containing action recommendations."""
    request_id: str
    timestamp: str
    actions: List[ActionRecommendation]
    recommended_action_id: Optional[str] = None


class PredictiveActionsClient:
    """Client for calling predictive actions API and managing UI interactions."""
    
    def __init__(self, api_url: str = "http://localhost:8000", timeout: int = 10):
        """Initialize the client.
        
        Args:
            api_url: Base URL of the ci-failure-agent API
            timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_predictive_actions(
        self,
        failure_description: str,
        failure_type: str,
        context: Optional[Dict] = None,
        severity: str = "medium",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> PredictiveActionsResponse:
        """Get predictive action recommendations from the API.
        
        Args:
            failure_description: Description of CI failure or incident
            failure_type: Type of incident (ci_failure, spam_incident, security_alert)
            context: Additional context information
            severity: Incident severity (low, medium, high, critical)
            user_id: User identifier for analytics
            session_id: Session identifier for tracking
            
        Returns:
            PredictiveActionsResponse with recommended actions
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        try:
            url = f"{self.api_url}/api/predictive_actions"
            payload = {
                "failure_description": failure_description,
                "failure_type": failure_type,
                "context": context or {},
                "severity": severity,
                "user_id": user_id,
                "session_id": session_id
            }
            
            logger.info(f"Calling predictive actions API for {failure_type}")
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"API error: {response.status}")
                    raise Exception(f"API returned status {response.status}")
                
                data = await response.json()
                
                # Convert to ActionRecommendation objects
                actions = [
                    ActionRecommendation(
                        action_id=action["action_id"],
                        title=action["title"],
                        description=action["description"],
                        action_type=action["action_type"],
                        priority=action["priority"],
                        estimated_time=action.get("estimated_time"),
                        success_rate=action.get("success_rate")
                    )
                    for action in data.get("actions", [])
                ]
                
                response_obj = PredictiveActionsResponse(
                    request_id=data["request_id"],
                    timestamp=data["timestamp"],
                    actions=actions,
                    recommended_action_id=data.get("recommended_action_id")
                )
                
                logger.info(f"Received {len(actions)} action recommendations")
                return response_obj
                
        except Exception as e:
            logger.error(f"Error calling predictive actions API: {str(e)}")
            raise
    
    async def log_action_selection(
        self,
        request_id: str,
        action_id: str,
        outcome: Optional[str] = None,
        feedback: Optional[str] = None
    ) -> Dict:
        """Log user's action selection for ML model training.
        
        Args:
            request_id: Original request ID
            action_id: Selected action ID
            outcome: Result of action (successful, failed, partial)
            feedback: User feedback on action
            
        Returns:
            Confirmation response
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        try:
            url = f"{self.api_url}/api/actions/log_selection"
            payload = {
                "request_id": request_id,
                "action_id": action_id,
                "selected_at": datetime.utcnow().isoformat(),
                "outcome": outcome,
                "feedback": feedback
            }
            
            logger.info(f"Logging action selection: {action_id}")
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Logging API error: {response.status}")
                    raise Exception(f"Logging API returned status {response.status}")
                
                data = await response.json()
                logger.info(f"Action selection logged successfully")
                return data
                
        except Exception as e:
            logger.error(f"Error logging action selection: {str(e)}")
            raise
    
    async def get_action_logs(self, limit: int = 100) -> Dict:
        """Retrieve logged action selections for analysis.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            Dictionary with logs and total count
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        try:
            url = f"{self.api_url}/api/actions/logs"
            params = {"limit": limit}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Get logs API error: {response.status}")
                    raise Exception(f"API returned status {response.status}")
                
                return await response.json()
                
        except Exception as e:
            logger.error(f"Error retrieving action logs: {str(e)}")
            raise


class PlatformUIActionPresenter:
    """Presents predictive actions in platform UI format."""
    
    @staticmethod
    def format_actions_for_ui(actions_response: PredictiveActionsResponse) -> Dict:
        """Format actions response for platform UI display.
        
        Converts API response into UI-friendly format for:
        - Alert notifications
        - Action recommendation panels
        - User interaction widgets
        
        Args:
            actions_response: Response from predictive actions API
            
        Returns:
            UI-formatted dictionary
        """
        ui_format = {
            "request_id": actions_response.request_id,
            "timestamp": actions_response.timestamp,
            "total_actions": len(actions_response.actions),
            "recommended_index": 0,  # Index of recommended action
            "actions": []
        }
        
        # Format each action for UI
        for idx, action in enumerate(actions_response.actions):
            is_recommended = action.action_id == actions_response.recommended_action_id
            
            action_ui = {
                "id": action.action_id,
                "title": action.title,
                "description": action.description,
                "type": action.action_type,
                "priority_level": ["critical", "high", "medium", "low"][min(action.priority - 1, 3)],
                "estimated_time": action.estimated_time or "Unknown",
                "confidence_score": round((action.success_rate or 0) * 100),
                "is_recommended": is_recommended,
                "action_buttons": {
                    "primary": "Execute" if action.action_type == "auto_fix" else "Confirm",
                    "secondary": "Learn More",
                    "tertiary": "Dismiss"
                }
            }
            
            ui_format["actions"].append(action_ui)
            
            if is_recommended:
                ui_format["recommended_index"] = idx
        
        return ui_format
    
    @staticmethod
    def get_action_display_template(action_type: str) -> str:
        """Get HTML/template snippet for action type.
        
        Args:
            action_type: Type of action
            
        Returns:
            HTML template snippet
        """
        templates = {
            "auto_fix": "<button class='action-auto-fix'>🔧 Execute Fix</button>",
            "manual_review": "<button class='action-manual'>👁 Review Details</button>",
            "escalate": "<button class='action-escalate'>⚠ Escalate</button>",
            "ignore": "<button class='action-ignore'>✓ Dismiss</button>"
        }
        return templates.get(action_type, "<button class='action-default'>Action</button>")


# Example usage for integration with alert handlers
async def handle_ci_failure_alert(failure_info: Dict) -> Optional[PredictiveActionsResponse]:
    """Handle CI failure alert and get recommendations.
    
    Args:
        failure_info: CI failure information
        
    Returns:
        Predictive actions response or None if error
    """
    try:
        async with PredictiveActionsClient() as client:
            response = await client.get_predictive_actions(
                failure_description=failure_info.get("message", ""),
                failure_type="ci_failure",
                context=failure_info.get("context", {}),
                severity=failure_info.get("severity", "medium"),
                user_id=failure_info.get("user_id"),
                session_id=failure_info.get("session_id")
            )
            return response
    except Exception as e:
        logger.error(f"Error handling CI failure alert: {str(e)}")
        return None
