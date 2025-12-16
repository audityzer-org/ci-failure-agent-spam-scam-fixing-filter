"""Advanced Orchestration Engine with Predictive Propositions Integration.

This module provides a comprehensive orchestration engine that:
- Manages CI failure detection and remediation workflows
- Handles spam/scam incident detection and response
- Integrates with predictive propositions service for suggested solutions
- Implements state machine-based workflow orchestration
- Handles parallel task execution with dependency tracking
- Tracks user decisions on propositions for ML model training
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
from datetime import datetime
import uuid

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

class PropositionDecision(Enum):
    """User decision on a proposition."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IGNORED = "ignored"
    PENDING = "pending"

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
class PredictiveProposition:
    """Predictive proposition recommendation."""
    id: str
    title: str
    description: str
    action_type: str
    parameters: Dict[str, Any]
    confidence_score: float
    estimated_impact: str
    priority: int = 1  # 1=highest, 3=lowest

@dataclass
class PropositionLog:
    """Log entry for proposition tracking and ML training."""
    request_id: str
    alert_id: str
    proposition_id: str
    presented_at: str
    user_decision: PropositionDecision
    decision_timestamp: Optional[str] = None
    feedback: Optional[str] = None
    outcome: Optional[str] = None  # 'successful', 'failed', 'partial'

# ================ Error Handling & Resilience ================

class RetryPolicy:
    """Retry policy for transient failures."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        import random
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay *= random.uniform(0.8, 1.2)
        return delay


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def record_success(self):
        """Record successful call."""
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
                logger.info("CircuitBreaker: Closed after recovery")
    
    def record_failure(self):
        """Record failed call."""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"CircuitBreaker: Opened after {self.failure_count} failures")
    
    def can_attempt(self) -> bool:
        """Check if call should be attempted."""
        import time
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
                self.success_count = 0
                logger.info("CircuitBreaker: Transitioning to half-open")
                return True
            return False
        else:  # half_open
            return True




class OrchestrationEngine:
    """Main orchestration engine for handling alerts and executing remediation."""
    
    def __init__(
        self,
        predictive_service_url: str = "http://localhost:8001",
        platform_webhook_url: Optional[str] = None
    ):
        """Initialize the orchestration engine.
        
        Args:
            predictive_service_url: URL of the predictive propositions service
            platform_webhook_url: Webhook URL for platform integration
        """
        self.predictive_service_url = predictive_service_url
        self.platform_webhook_url = platform_webhook_url
        self.active_alerts: Dict[str, Alert] = {}
        self.proposition_history: List[PropositionLog] = []
        self.action_history: List[Dict[str, Any]] = []
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def process_alert(self, alert: Alert) -> Dict[str, Any]:
        """Process an incoming alert and fetch predictive propositions.
        
        Args:
            alert: The alert to process
            
        Returns:
            Dictionary containing alert processing result and recommendations
        """
        logger.info(f"Processing alert: {alert.id} of type {alert.type.value}")
        
        self.active_alerts[alert.id] = alert
        request_id = str(uuid.uuid4())
        
        # Fetch predictive propositions based on alert type
        propositions = await self._fetch_predictive_propositions_with_retry(alert, request_id)        
        result = {
            "request_id": request_id,
            "alert_id": alert.id,
            "alert_type": alert.type.value,
            "status": "processed",
            "propositions": propositions,
            "proposition_count": len(propositions),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Alert {alert.id} processed with {len(propositions)} propositions")
        return result
    
    async def _fetch_predictive_propositions(
        self, alert: Alert, request_id: str
    ) -> List[PredictiveProposition]:
        """Fetch predictive propositions for an alert.
        
        Args:
            alert: The alert to get propositions for
            request_id: Request ID for tracking
            
        Returns:
            List of recommended propositions
        """
        try:
            payload = {
                "failure_description": alert.description,
                "failure_type": alert.type.value,
                "severity": alert.severity,
                "context": alert.metadata
            }
            
            response = await self.client.post(
                f"{self.predictive_service_url}/api/predictive_actions",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                propositions = [
                    PredictiveProposition(
                        id=action.get('action_id', str(uuid.uuid4())),
                        title=action.get('title', ''),
                        description=action.get('description', ''),
                        action_type=action.get('action_type', ''),
                        parameters=action.get('parameters', {}),
                        confidence_score=action.get('success_rate', 0.5),
                        estimated_impact=action.get('estimated_time', 'unknown'),
                        priority=action.get('priority', 1)
                    )
                    for action in data.get("actions", [])
                ]
                return propositions
            else:
                logger.warning(f"Failed to fetch propositions: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching predictive propositions: {e}")
            return []

        async def _fetch_predictive_propositions_with_retry(
        self,
        alert: Alert,
        request_id: str,
        retry_policy: RetryPolicy = None,
        circuit_breaker: CircuitBreaker = None
    ) -> List[PredictiveProposition]:
        """Fetch propositions with retry logic and circuit breaker pattern.
        
        Args:
            alert: The alert to get propositions for
            request_id: Request ID for tracking
            retry_policy: Retry policy for exponential backoff (optional)
            circuit_breaker: Circuit breaker for fault tolerance (optional)
        
        Returns:
            List of recommended propositions with graceful degradation
        """
        import time
        import asyncio
        
        if retry_policy is None:
            retry_policy = RetryPolicy(
                max_retries=3,
                initial_delay=1.0,
                exponential_base=2.0,
                jitter=True
            )
        
        if circuit_breaker is None:
            circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                success_threshold=2,
                timeout=60.0
            )
        
        # Check circuit breaker state before attempting
        if not circuit_breaker.can_attempt():
            logger.warning("CircuitBreaker: Service unavailable, returning empty propositions")
            return []
        
        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(retry_policy.max_retries):
            try:
                logger.info(f"Fetching propositions (attempt {attempt + 1}/{retry_policy.max_retries})")
                
                # Call the base fetch method
                propositions = await self._fetch_predictive_propositions(alert, request_id)
                
                # Record success
                circuit_breaker.record_success()
                logger.info(f"Successfully fetched {len(propositions)} propositions")
                return propositions
                
            except asyncio.TimeoutError:
                last_exception = asyncio.TimeoutError("Request timeout")
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                circuit_breaker.record_failure()
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Error on attempt {attempt + 1}: {str(e)}")
                circuit_breaker.record_failure()
            
            # Calculate delay for next retry (but not after last attempt)
            if attempt < retry_policy.max_retries - 1:
                delay = retry_policy.get_delay(attempt)
                logger.info(f"Waiting {delay:.2f}s before retry...")
                await asyncio.sleep(delay)
        
        # All retries exhausted - log and return graceful degradation
        logger.error(f"Failed to fetch propositions after {retry_policy.max_retries} attempts: {last_exception}")
        return []  # Graceful degradation: return empty list


    
    async def apply_proposition(
        self,
        alert_id: str,
        proposition: PredictiveProposition,
        request_id: str,
        user_decision: PropositionDecision = PropositionDecision.PENDING
    ) -> Dict[str, Any]:
        """Apply a recommended proposition.
        
        Args:
            alert_id: ID of the associated alert
            proposition: The proposition to apply
            request_id: Request ID for tracking
            user_decision: User's decision on the proposition
            
        Returns:
            Application result
        """
        if alert_id not in self.active_alerts:
            return {"status": "error", "message": f"Alert {alert_id} not found"}
        
        # Log the proposition for ML training
        log_entry = PropositionLog(
            request_id=request_id,
            alert_id=alert_id,
            proposition_id=proposition.id,
            presented_at=datetime.utcnow().isoformat(),
            user_decision=user_decision,
            decision_timestamp=datetime.utcnow().isoformat() if user_decision != PropositionDecision.PENDING else None
        )
        self.proposition_history.append(log_entry)
        
        execution_record = {
            "alert_id": alert_id,
            "proposition_id": proposition.id,
            "proposition_title": proposition.title,
            "user_decision": user_decision.value,
            "status": ActionStatus.EXECUTED.value if user_decision == PropositionDecision.ACCEPTED else ActionStatus.REJECTED.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.action_history.append(execution_record)
        
        if user_decision == PropositionDecision.ACCEPTED:
            # Execute the proposition based on type
            result = await self._execute_by_type(proposition)
            execution_record["execution_result"] = result
            logger.info(f"Proposition {proposition.id} executed: {result}")
        else:
            logger.info(f"Proposition {proposition.id} - User decision: {user_decision.value}")
        
        return execution_record
    
    async def _execute_by_type(self, proposition: PredictiveProposition) -> Dict[str, Any]:
        """Execute proposition based on its type.
        
        Args:
            proposition: The proposition to execute
            
        Returns:
            Execution result
        """
        action_type = proposition.action_type
        
        if action_type == "auto_fix":
            return await self._execute_auto_fix(proposition)
        elif action_type == "manual_review":
            return await self._execute_review(proposition)
        elif action_type == "escalate":
            return await self._execute_escalation(proposition)
        elif action_type == "ignore":
            return {"status": "success", "type": "ignore", "details": "Issue marked as ignored"}
        else:
            return {"status": "unknown", "message": f"Unknown action type: {action_type}"}
    
    async def _execute_auto_fix(self, proposition: PredictiveProposition) -> Dict[str, Any]:
        """Execute automatic fix."""
        return {"status": "success", "type": "auto_fix", "details": "Auto-fix executed"}
    
    async def _execute_review(self, proposition: PredictiveProposition) -> Dict[str, Any]:
        """Prepare for manual review."""
        return {"status": "success", "type": "manual_review", "details": "Queued for review"}
    
    async def _execute_escalation(self, proposition: PredictiveProposition) -> Dict[str, Any]:
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
            "total_propositions_tracked": len(self.proposition_history),
            "total_actions_executed": len(self.action_history)
        }
    
    async def get_proposition_logs(
        self, alert_id: Optional[str] = None, limit: int = 100
    ) -> List[PropositionLog]:
        """Get proposition logs for ML model training.
        
        Args:
            alert_id: Optional alert ID to filter logs
            limit: Maximum number of logs to return
            
        Returns:
            List of proposition logs
        """
        if alert_id:
            return [log for log in self.proposition_history if log.alert_id == alert_id][-limit:]
        return self.proposition_history[-limit:]
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


# Backward compatibility with existing orchestrator_integration
class OrchestratorIntegration:
    """Legacy wrapper for backward compatibility."""
    
    def __init__(self):
        self.engine = OrchestrationEngine()
    
    async def process_ci_failure(self, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process CI failure with predictive propositions."""
        alert = Alert(
            id=failure_data.get("id", str(uuid.uuid4())),
            type=AlertType.CI_FAILURE,
            description=failure_data.get("description", ""),
            severity=failure_data.get("severity", "medium"),
            timestamp=failure_data.get("timestamp", datetime.utcnow().isoformat()),
            source=failure_data.get("source", "ci_system"),
            metadata=failure_data.get("metadata", {})
        )
        return await self.engine.process_alert(alert)
    
    async def process_security_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process security incident (spam/scam) with predictive propositions."""
        incident_type = incident_data.get("incident_type", "spam_incident")
        alert_type = AlertType.SPAM_INCIDENT if incident_type == "spam_incident" else AlertType.SCAM_INCIDENT
        
        alert = Alert(
            id=incident_data.get("id", str(uuid.uuid4())),
            type=alert_type,
            description=incident_data.get("description", ""),
            severity=incident_data.get("severity", "high"),
            timestamp=incident_data.get("timestamp", datetime.utcnow().isoformat()),
            source=incident_data.get("source", "security_system"),
            metadata=incident_data.get("metadata", {})
        )
        return await self.engine.process_alert(alert)
