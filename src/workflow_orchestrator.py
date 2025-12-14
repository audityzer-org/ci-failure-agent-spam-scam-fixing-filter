#!/usr/bin/env python3
"""
Phase 2: Workflow Orchestration & State Management Engine
Automates complex workflows across all 4 microservices with intelligent routing.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    VALIDATING = "VALIDATING"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class RetryPolicy:
    """Exponential backoff retry mechanism"""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with exponential backoff"""
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)


@dataclass
class WorkflowStep:
    """Individual workflow step configuration"""
    id: str
    service: str  # anti-corruption-orchestrator, spam-detection, compliance-validator, audit-trail-aggregator
    action: str  # investigate, validate, remediate, etc.
    depends_on: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    retry_policy: Optional[RetryPolicy] = None


@dataclass
class WorkflowInstance:
    """Active workflow execution instance"""
    id: str
    case_id: str
    state: WorkflowState
    steps: Dict[str, WorkflowStep]
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_status: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator:
    """Orchestrates complex multi-service workflows with DAG execution"""
    
    def __init__(self):
        self.workflows: Dict[str, WorkflowInstance] = {}
        self.service_registry: Dict[str, str] = {}  # service_name -> endpoint
        self.event_bus = None  # Will be initialized with event system
        
    async def register_service(self, service_name: str, endpoint: str):
        """Register a microservice endpoint"""
        self.service_registry[service_name] = endpoint
        logger.info(f"Registered service {service_name} at {endpoint}")
    
    async def create_workflow(self, case_id: str, steps: List[WorkflowStep]) -> WorkflowInstance:
        """Create a new workflow instance"""
        workflow_id = str(uuid.uuid4())
        
        steps_dict = {step.id: step for step in steps}
        workflow = WorkflowInstance(
            id=workflow_id,
            case_id=case_id,
            state=WorkflowState.PENDING,
            steps=steps_dict
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id} for case {case_id}")
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> WorkflowInstance:
        """Execute workflow with DAG-based dependency resolution"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        workflow.state = WorkflowState.INVESTIGATING
        
        try:
            # Topological sort for DAG execution
            execution_order = self._topological_sort(workflow)
            
            for step_id in execution_order:
                step = workflow.steps[step_id]
                logger.info(f"Executing step {step_id}: {step.action}")
                
                try:
                    # Prepare payload with results from dependent steps
                    enriched_payload = step.payload.copy()
                    for dep_id in step.depends_on:
                        if dep_id in workflow.step_results:
                            enriched_payload[f"{dep_id}_result"] = workflow.step_results[dep_id]
                    
                    # Execute step with retry policy
                    retry_policy = step.retry_policy or RetryPolicy()
                    result = await retry_policy.execute(
                        self._call_service,
                        step.service,
                        step.action,
                        enriched_payload
                    )
                    
                    workflow.step_results[step_id] = result
                    workflow.step_status[step_id] = "completed"
                    
                except asyncio.TimeoutError:
                    logger.error(f"Step {step_id} timed out")
                    workflow.step_status[step_id] = "timeout"
                    raise
                except Exception as e:
                    logger.error(f"Step {step_id} failed: {e}")
                    workflow.step_status[step_id] = "failed"
                    raise
            
            workflow.state = WorkflowState.RESOLVED
            
        except Exception as e:
            workflow.state = WorkflowState.FAILED
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise
        finally:
            workflow.updated_at = datetime.utcnow()
        
        return workflow
    
    def _topological_sort(self, workflow: WorkflowInstance) -> List[str]:
        """Topologically sort workflow steps by dependencies"""
        visited = set()
        order = []
        
        def visit(step_id: str):
            if step_id in visited:
                return
            visited.add(step_id)
            
            step = workflow.steps[step_id]
            for dep_id in step.depends_on:
                visit(dep_id)
            
            order.append(step_id)
        
        for step_id in workflow.steps:
            visit(step_id)
        
        return order
    
    async def _call_service(self, service_name: str, action: str, payload: Dict[str, Any]) -> Any:
        """Call a microservice asynchronously"""
        if service_name not in self.service_registry:
            raise ValueError(f"Service {service_name} not registered")
        
        endpoint = self.service_registry[service_name]
        # This would use httpx or aiohttp in production
        logger.info(f"Calling {service_name}/{action} with payload: {json.dumps(payload)}")
        
        # Simulated service call - replace with actual HTTP call
        await asyncio.sleep(0.1)
        return {"status": "success", "service": service_name, "action": action}
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        return {
            "id": workflow.id,
            "case_id": workflow.case_id,
            "state": workflow.state.value,
            "step_status": workflow.step_status,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat()
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        if workflow.state not in [WorkflowState.PENDING, WorkflowState.INVESTIGATING]:
            return False
        
        workflow.state = WorkflowState.FAILED
        logger.info(f"Cancelled workflow {workflow_id}")
        return True


# Example usage
async def main():
    orchestrator = WorkflowOrchestrator()
    
    # Register services
    await orchestrator.register_service("anti-corruption-orchestrator", "http://localhost:8001")
    await orchestrator.register_service("spam-detection", "http://localhost:8002")
    await orchestrator.register_service("compliance-validator", "http://localhost:8003")
    await orchestrator.register_service("audit-trail-aggregator", "http://localhost:8004")
    
    # Create workflow steps
    steps = [
        WorkflowStep(
            id="step1",
            service="anti-corruption-orchestrator",
            action="investigate",
            payload={"case_id": "case-123", "reason": "spam"}
        ),
        WorkflowStep(
            id="step2",
            service="spam-detection",
            action="analyze",
            depends_on=["step1"],
            payload={"threshold": 0.8}
        ),
        WorkflowStep(
            id="step3",
            service="compliance-validator",
            action="validate",
            depends_on=["step1", "step2"],
            payload={"rules": ["spam_policy", "compliance_policy"]}
        ),
        WorkflowStep(
            id="step4",
            service="audit-trail-aggregator",
            action="log",
            depends_on=["step3"],
            payload={"event_type": "case_resolved"}
        )
    ]
    
    # Create and execute workflow
    workflow = await orchestrator.create_workflow("case-123", steps)
    await orchestrator.execute_workflow(workflow.id)
    
    # Get status
    status = await orchestrator.get_workflow_status(workflow.id)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
