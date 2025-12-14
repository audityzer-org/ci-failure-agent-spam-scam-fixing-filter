"""REST API endpoint for predictive actions suggestions.

Provides recommendations for handling CI failures, spam/scam incidents,
and alerts based on incident description and context.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["predictive-actions"])


class PredictiveActionRequest(BaseModel):
    """Request model for predictive actions endpoint."""
    failure_description: str
    failure_type: str  # e.g., 'ci_failure', 'spam_incident', 'security_alert'
    context: Optional[Dict[str, str]] = None
    severity: Optional[str] = "medium"  # low, medium, high, critical
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class PredictiveAction(BaseModel):
    """Single predictive action suggestion."""
    action_id: str
    title: str
    description: str
    action_type: str  # e.g., 'auto_fix', 'manual_review', 'escalate', 'ignore'
    priority: int  # 1=highest, 3=lowest
    estimated_time: Optional[str] = None
    success_rate: Optional[float] = None  # ML model confidence


class PredictiveActionResponse(BaseModel):
    """Response model with suggested actions."""
    request_id: str
    timestamp: str
    actions: List[PredictiveAction]
    recommended_action_id: Optional[str] = None


class ActionSelectionLog(BaseModel):
    """Log for user action selection (for ML training)."""
    request_id: str
    action_id: str
    selected_at: str
    outcome: Optional[str] = None  # 'successful', 'failed', 'partial'
    feedback: Optional[str] = None


# In-memory storage for action selection logs (in production: use database)
_action_logs: List[ActionSelectionLog] = []


def get_ci_failure_actions(description: str, context: Dict = None) -> List[PredictiveAction]:
    """Generate predictive actions for CI failures."""
    actions = [
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Retry Failed Job",
            description="Automatically retry the failed CI job with current configuration",
            action_type="auto_fix",
            priority=1,
            estimated_time="2-5 minutes",
            success_rate=0.72
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Review Build Logs",
            description="Open detailed build logs and error analysis for manual inspection",
            action_type="manual_review",
            priority=1,
            estimated_time="5-15 minutes",
            success_rate=0.85
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Run Diagnostics",
            description="Execute diagnostic checks to identify environmental or dependency issues",
            action_type="auto_fix",
            priority=2,
            estimated_time="3-10 minutes",
            success_rate=0.68
        ),
    ]
    return actions


def get_spam_scam_actions(description: str, context: Dict = None) -> List[PredictiveAction]:
    """Generate predictive actions for spam/scam incidents."""
    actions = [
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Quarantine & Review",
            description="Move item to quarantine for manual security team review",
            action_type="manual_review",
            priority=1,
            estimated_time="immediate",
            success_rate=0.92
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Block & Report",
            description="Block sender/source and report to abuse authorities",
            action_type="escalate",
            priority=1,
            estimated_time="immediate",
            success_rate=0.88
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Additional Verification",
            description="Request additional security verification from user",
            action_type="manual_review",
            priority=2,
            estimated_time="5-10 minutes",
            success_rate=0.75
        ),
    ]
    return actions


def get_security_alert_actions(description: str, context: Dict = None) -> List[PredictiveAction]:
    """Generate predictive actions for security alerts."""
    actions = [
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Escalate to Security Team",
            description="Immediately escalate to security operations center for investigation",
            action_type="escalate",
            priority=1,
            estimated_time="immediate",
            success_rate=0.95
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Isolate Affected Resources",
            description="Isolate affected systems to prevent further compromise",
            action_type="auto_fix",
            priority=1,
            estimated_time="1-3 minutes",
            success_rate=0.90
        ),
        PredictiveAction(
            action_id=str(uuid.uuid4()),
            title="Enable Enhanced Monitoring",
            description="Enable enhanced monitoring and logging on affected resources",
            action_type="auto_fix",
            priority=2,
            estimated_time="immediate",
            success_rate=0.87
        ),
    ]
    return actions


@router.post("/predictive_actions", response_model=PredictiveActionResponse)
async def get_predictive_actions(request: PredictiveActionRequest) -> PredictiveActionResponse:
    """Get predictive action suggestions for CI failures, alerts, or security incidents.
    
    Args:
        request: PredictiveActionRequest containing failure description and context
        
    Returns:
        PredictiveActionResponse with 2-3 recommended actions
        
    Example:
        POST /api/predictive_actions
        {
            "failure_description": "Docker image build failed: base image not found",
            "failure_type": "ci_failure",
            "severity": "high"
        }
    """
    try:
        request_id = str(uuid.uuid4())
        logger.info(f"Processing predictive action request {request_id}: {request.failure_type}")
        
        # Select actions based on failure type
        if request.failure_type == "ci_failure":
            actions = get_ci_failure_actions(request.failure_description, request.context)
        elif request.failure_type == "spam_incident":
            actions = get_spam_scam_actions(request.failure_description, request.context)
        elif request.failure_type == "security_alert":
            actions = get_security_alert_actions(request.failure_description, request.context)
        else:
            # Default to CI failure actions for unknown types
            actions = get_ci_failure_actions(request.failure_description, request.context)
        
        # Return top 2-3 actions based on priority and success rate
        actions_sorted = sorted(actions, key=lambda x: (-x.priority, -x.success_rate))[:3]
        
        response = PredictiveActionResponse(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            actions=actions_sorted,
            recommended_action_id=actions_sorted[0].action_id if actions_sorted else None
        )
        
        logger.info(f"Generated {len(actions_sorted)} actions for request {request_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating predictive actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating predictive actions: {str(e)}")


@router.post("/actions/log_selection")
async def log_action_selection(log: ActionSelectionLog):
    """Log user selection of a predictive action for ML model training.
    
    Args:
        log: ActionSelectionLog containing selection details
        
    Returns:
        Confirmation of logged selection
    """
    try:
        _action_logs.append(log)
        logger.info(f"Logged action selection for request {log.request_id}: action {log.action_id}")
        
        return {
            "status": "logged",
            "request_id": log.request_id,
            "timestamp": log.selected_at,
            "total_logs": len(_action_logs)
        }
    except Exception as e:
        logger.error(f"Error logging action selection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error logging selection: {str(e)}")


@router.get("/actions/logs")
async def get_action_logs(limit: int = 100):
    """Retrieve logged action selections (for ML model training).
    
    Args:
        limit: Maximum number of logs to return
        
    Returns:
        List of ActionSelectionLog entries
    """
    return {"total": len(_action_logs), "logs": _action_logs[-limit:]}


@router.health("/health")
async def health_check():
    """Health check endpoint for predictive actions service."""
    return {"status": "healthy", "service": "predictive_actions_api"}
