"""Integration module for Phase 2 components

Integrates WorkflowOrchestrator, StateMachine, and TaskQueue
into a unified orchestration system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from task_queue import TaskQueue, TaskPriority, TaskStatus
from workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
from state_machine import StateMachine, CaseState
from service_integration_gateway import ServiceIntegrationGateway

logger = logging.getLogger(__name__)


class OrchestratorIntegration:
    """Unified orchestration system integrating all Phase 2 components"""
    
    def __init__(
        self,
        task_queue: TaskQueue,
        workflow_orchestrator: WorkflowOrchestrator,
        state_machine: StateMachine,
        service_gateway: ServiceIntegrationGateway
    ):
        """Initialize orchestrator integration
        
        Args:
            task_queue: Redis-backed task queue
            workflow_orchestrator: DAG-based workflow executor
            state_machine: Case lifecycle state machine
            service_gateway: Service integration gateway
        """
        self.task_queue = task_queue
        self.workflow = workflow_orchestrator
        self.state_machine = state_machine
        self.service_gateway = service_gateway
        self.case_workflows: Dict[str, Dict[str, Any]] = {}
    
    async def process_case(
        self,
        case_id: str,
        case_data: Dict[str, Any],
        workflow_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a case through the orchestration pipeline
        
        Args:
            case_id: Case ID
            case_data: Case data
            workflow_definition: Workflow definition
            
        Returns:
            Processing result
        """
        try:
            # Initialize case state
            self.state_machine.initialize_case(case_id)
            self.state_machine.transition_case(case_id, CaseState.INVESTIGATING, "Starting investigation")
            
            # Create workflow instance
            workflow_steps = [
                WorkflowStep(
                    name=step['name'],
                    service_name=step['service'],
                    payload=step.get('payload', {}),
                    dependencies=step.get('depends_on', [])
                )
                for step in workflow_definition.get('steps', [])
            ]
            
            workflow_instance = self.workflow.execute_workflow(
                workflow_id=case_id,
                steps=workflow_steps,
                context=case_data
            )
            
            # Store workflow reference
            self.case_workflows[case_id] = {
                'workflow': workflow_instance,
                'created_at': datetime.utcnow(),
                'status': 'executing'
            }
            
            # Enqueue processing tasks
            for step in workflow_steps:
                task = self.task_queue.enqueue(
                    task_type='execute_workflow_step',
                    payload={
                        'case_id': case_id,
                        'step_name': step.name,
                        'service_name': step.service_name,
                        'payload': step.payload
                    },
                    priority=TaskPriority.HIGH
                )
                logger.info(f"Enqueued task {task.task_id} for case {case_id} step {step.name}")
            
            return {
                'case_id': case_id,
                'status': 'processing',
                'workflow_instance': workflow_instance
            }
        
        except Exception as e:
            logger.error(f"Error processing case {case_id}: {str(e)}")
            self.state_machine.transition_case(case_id, CaseState.FAILED, f"Error: {str(e)}")
            return {
                'case_id': case_id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def process_task(self, task_id: str) -> Dict[str, Any]:
        """Process a single task from the queue
        
        Args:
            task_id: Task ID
            
        Returns:
            Task result
        """
        try:
            task = self.task_queue.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return {'status': 'not_found'}
            
            if task.task_type == 'execute_workflow_step':
                result = await self._execute_workflow_step(task)
                
                if result['success']:
                    self.task_queue.complete(task_id, result)
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    self.task_queue.fail(task_id, result.get('error', 'Unknown error'))
                    logger.warning(f"Task {task_id} failed: {result.get('error')}")
                
                return result
        
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            self.task_queue.fail(task_id, str(e))
            return {'success': False, 'error': str(e)}
    
    async def _execute_workflow_step(
        self,
        task: Any
    ) -> Dict[str, Any]:
        """Execute a workflow step
        
        Args:
            task: Task to execute
            
        Returns:
            Execution result
        """
        try:
            payload = task.payload
            case_id = payload['case_id']
            step_name = payload['step_name']
            service_name = payload['service_name']
            
            # Execute service
            result = await self.service_gateway.call_service(
                service_name=service_name,
                method='execute',
                payload=payload['payload']
            )
            
            # Update case state
            self.state_machine.transition_case(
                case_id,
                CaseState.VALIDATING,
                f"Completed step: {step_name}"
            )
            
            logger.info(f"Step {step_name} completed for case {case_id}")
            
            return {
                'success': True,
                'case_id': case_id,
                'step_name': step_name,
                'result': result
            }
        
        except Exception as e:
            logger.error(f"Error executing workflow step: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def worker_loop(self, poll_interval: int = 1):
        """Main worker loop for processing tasks
        
        Args:
            poll_interval: Polling interval in seconds
        """
        logger.info("Starting orchestrator worker loop")
        
        while True:
            try:
                # Dequeue task
                task = self.task_queue.dequeue()
                
                if task:
                    await self.process_task(task.task_id)
                else:
                    await asyncio.sleep(poll_interval)
            
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                await asyncio.sleep(poll_interval)
    
    def get_case_status(self, case_id: str) -> Dict[str, Any]:
        """Get case status
        
        Args:
            case_id: Case ID
            
        Returns:
            Case status information
        """
        case_state = self.state_machine.get_case_state(case_id)
        workflow_info = self.case_workflows.get(case_id, {})
        queue_stats = self.task_queue.get_stats()
        
        return {
            'case_id': case_id,
            'state': case_state.name if case_state else 'unknown',
            'workflow_status': workflow_info.get('status', 'unknown'),
            'queue_stats': queue_stats
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics
        
        Returns:
            System statistics
        """
        return {
            'active_cases': len(self.case_workflows),
            'queue_stats': self.task_queue.get_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
