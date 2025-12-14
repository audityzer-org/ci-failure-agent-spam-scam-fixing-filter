#!/usr/bin/env python3
"""
Phase 3: Comprehensive Integration Tests
Unit, integration, load, and end-to-end tests for all microservices
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import List
import json


class TestWorkflowOrchestrator:
    """Unit tests for workflow orchestration"""
    
    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        """Test creating a new workflow instance"""
        # Mock orchestrator
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        orchestrator = WorkflowOrchestrator()
        
        steps = [WorkflowStep(
            id="step1",
            service="test-service",
            action="test-action",
            payload={"test": "data"}
        )]
        
        workflow = await orchestrator.create_workflow("case-123", steps)
        assert workflow.case_id == "case-123"
        assert len(workflow.steps) == 1
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """Test executing a workflow with DAG"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        orchestrator = WorkflowOrchestrator()
        await orchestrator.register_service("test-service", "http://localhost:8000")
        
        steps = [WorkflowStep(
            id="step1",
            service="test-service",
            action="test",
            payload={}
        )]
        
        workflow = await orchestrator.create_workflow("case-123", steps)
        result = await orchestrator.execute_workflow(workflow.id)
        assert result.state.value == "RESOLVED"
    
    def test_topological_sort(self):
        """Test DAG topological sorting"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep, WorkflowInstance, WorkflowState
        orchestrator = WorkflowOrchestrator()
        
        steps = {
            "step1": WorkflowStep("step1", "svc", "act", []),
            "step2": WorkflowStep("step2", "svc", "act", ["step1"]),
            "step3": WorkflowStep("step3", "svc", "act", ["step1", "step2"])
        }
        
        workflow = WorkflowInstance("wf1", "case1", WorkflowState.PENDING, steps)
        order = orchestrator._topological_sort(workflow)
        
        assert order.index("step1") < order.index("step2")
        assert order.index("step2") < order.index("step3")


class TestStateMachine:
    """Unit tests for state machine"""
    
    @pytest.mark.asyncio
    async def test_state_transition(self):
        """Test valid state transitions"""
        from src.state_machine import StateMachine, CaseState
        machine = StateMachine("case-123")
        
        result = await machine.transition(CaseState.INVESTIGATING, "Start investigation")
        assert result is True
        assert machine.get_state() == CaseState.INVESTIGATING
    
    @pytest.mark.asyncio
    async def test_invalid_transition(self):
        """Test invalid state transitions are rejected"""
        from src.state_machine import StateMachine, CaseState
        machine = StateMachine("case-123", CaseState.RESOLVED)
        
        result = await machine.transition(CaseState.INVESTIGATING, "Invalid transition")
        assert result is False
        assert machine.get_state() == CaseState.RESOLVED
    
    def test_state_serialization(self):
        """Test state machine serialization"""
        from src.state_machine import StateMachine, CaseState
        machine = StateMachine("case-123")
        
        data = machine.to_dict()
        assert data["case_id"] == "case-123"
        assert data["current_state"] == CaseState.PENDING.value
        assert data["is_terminal"] is False


class TestMultiServiceIntegration:
    """Integration tests across multiple services"""
    
    @pytest.mark.asyncio
    async def test_anti_corruption_spam_flow(self):
        """Test anti-corruption + spam detection workflow"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        from src.state_machine import StateMachineManager, CaseState
        
        orchestrator = WorkflowOrchestrator()
        sm_manager = StateMachineManager()
        
        # Register services
        await orchestrator.register_service("anti-corruption", "http://localhost:8001")
        await orchestrator.register_service("spam-detection", "http://localhost:8002")
        
        # Create workflow
        steps = [
            WorkflowStep("investigate", "anti-corruption", "investigate", payload={"case": "spam"}),
            WorkflowStep("analyze", "spam-detection", "analyze", depends_on=["investigate"], payload={"threshold": 0.8})
        ]
        
        workflow = await orchestrator.create_workflow("case-456", steps)
        await orchestrator.execute_workflow(workflow.id)
        
        # Verify state transitions
        machine = sm_manager.create_machine("case-456")
        await machine.transition(CaseState.INVESTIGATING, "Evidence gathered")
        await machine.transition(CaseState.VALIDATING, "Spam confirmed")
        
        assert machine.get_state() == CaseState.VALIDATING
    
    @pytest.mark.asyncio
    async def test_compliance_audit_trail_flow(self):
        """Test compliance validator + audit trail aggregator workflow"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        
        orchestrator = WorkflowOrchestrator()
        await orchestrator.register_service("compliance", "http://localhost:8003")
        await orchestrator.register_service("audit-trail", "http://localhost:8004")
        
        steps = [
            WorkflowStep("validate", "compliance", "validate", payload={"rules": ["spam", "fraud"]}),
            WorkflowStep("log", "audit-trail", "log", depends_on=["validate"], payload={"event": "validation_complete"})
        ]
        
        workflow = await orchestrator.create_workflow("case-789", steps)
        result = await orchestrator.execute_workflow(workflow.id)
        
        assert result.state.value == "RESOLVED"
        assert "validate" in result.step_results
        assert "log" in result.step_results


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test exponential backoff retry"""
        from src.workflow_orchestrator import RetryPolicy
        
        retry_policy = RetryPolicy(max_retries=3, base_delay=0.1)
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry_policy.execute(failing_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_workflow_failure_handling(self):
        """Test graceful failure handling in workflows"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        
        orchestrator = WorkflowOrchestrator()
        
        # Mock failing service
        with patch.object(orchestrator, '_call_service', side_effect=Exception("Service error")):
            steps = [WorkflowStep("fail", "bad-service", "fail", payload={})]
            workflow = await orchestrator.create_workflow("case-fail", steps)
            
            with pytest.raises(Exception):
                await orchestrator.execute_workflow(workflow.id)
            
            assert workflow.state.value == "FAILED"


class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """Test handling 100 concurrent workflows"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        
        orchestrator = WorkflowOrchestrator()
        await orchestrator.register_service("test", "http://localhost:8000")
        
        start = time.time()
        
        async def create_and_execute(case_id):
            steps = [WorkflowStep(f"step-{case_id}", "test", "action", payload={})]
            workflow = await orchestrator.create_workflow(case_id, steps)
            return await orchestrator.execute_workflow(workflow.id)
        
        tasks = [create_and_execute(f"case-{i}") for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start
        assert len(results) == 100
        assert duration < 30  # Should complete in less than 30 seconds
    
    def test_state_machine_throughput(self):
        """Test state machine throughput (1000+ transitions)"""
        from src.state_machine import StateMachineManager, CaseState
        import asyncio
        
        manager = StateMachineManager()
        start = time.time()
        
        for i in range(1000):
            machine = manager.create_machine(f"perf-case-{i}")
            asyncio.run(machine.transition(CaseState.INVESTIGATING, "Fast"))
        
        duration = time.time() - start
        throughput = 1000 / duration
        
        assert throughput > 100  # At least 100 transitions/second


class TestEndToEnd:
    """End-to-end workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_spam_case_flow(self):
        """Test complete spam case from report to resolution"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        from src.state_machine import StateMachineManager, CaseState
        
        orchestrator = WorkflowOrchestrator()
        state_manager = StateMachineManager()
        
        # Register all services
        services = {
            "anti-corruption": "http://localhost:8001",
            "spam-detection": "http://localhost:8002",
            "compliance": "http://localhost:8003",
            "audit-trail": "http://localhost:8004"
        }
        
        for service, endpoint in services.items():
            await orchestrator.register_service(service, endpoint)
        
        # Create complete workflow
        steps = [
            WorkflowStep("investigate", "anti-corruption", "investigate", payload={"case": "spam-report"}),
            WorkflowStep("analyze", "spam-detection", "analyze", depends_on=["investigate"], payload={"threshold": 0.8}),
            WorkflowStep("validate", "compliance", "validate", depends_on=["analyze"], payload={"rules": ["spam_policy"]}),
            WorkflowStep("log", "audit-trail", "log", depends_on=["validate"], payload={"event": "case_resolved"})
        ]
        
        workflow = await orchestrator.create_workflow("e2e-case-spam", steps)
        result = await orchestrator.execute_workflow(workflow.id)
        
        # Verify workflow completed
        assert result.state.value == "RESOLVED"
        assert len(result.step_results) == 4
        
        # Verify state machine progression
        machine = state_manager.create_machine("e2e-case-spam")
        await machine.transition(CaseState.INVESTIGATING, "")
        await machine.transition(CaseState.VALIDATING, "")
        await machine.transition(CaseState.REMEDIATING, "")
        await machine.transition(CaseState.RESOLVED, "")
        
        assert machine.is_terminal()


# Test configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=html"])
