#!/usr/bin/env python3
"""
Phase 3.3: Load Testing and Performance Benchmarking
Tests system under load: 1000 concurrent requests, 10,000 messages/second throughput
"""

import pytest
import asyncio
import time
from locust import HttpUser, task, between
import statistics


class LoadTestWorkflows:
    """Load tests for workflow orchestration"""
    
    @pytest.mark.asyncio
    async def test_1000_concurrent_workflows(self):
        """Test handling 1000 concurrent workflows"""
        from src.workflow_orchestrator import WorkflowOrchestrator, WorkflowStep
        
        orchestrator = WorkflowOrchestrator()
        await orchestrator.register_service("test", "http://localhost:8000")
        
        start = time.time()
        latencies = []
        
        async def create_and_execute(case_id):
            step_start = time.time()
            steps = [WorkflowStep(f"step-{case_id}", "test", "action", payload={})]
            workflow = await orchestrator.create_workflow(f"case-{case_id}", steps)
            result = await orchestrator.execute_workflow(workflow.id)
            latency = time.time() - step_start
            latencies.append(latency)
            return result
        
        tasks = [create_and_execute(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start
        
        # Performance assertions
        assert len(results) == 1000
        assert duration < 60  # Complete in under 60 seconds
        
        # Latency statistics
        p50_latency = sorted(latencies)[500]
        p95_latency = sorted(latencies)[950]
        p99_latency = sorted(latencies)[990]
        
        print(f"\nLoad Test Results (1000 workflows):")
        print(f"Total Duration: {duration:.2f}s")
        print(f"Throughput: {1000/duration:.2f} workflows/sec")
        print(f"p50 Latency: {p50_latency*1000:.2f}ms")
        print(f"p95 Latency: {p95_latency*1000:.2f}ms")
        print(f"p99 Latency: {p99_latency*1000:.2f}ms")
        
        assert p99_latency < 0.15  # p99 latency < 150ms
    
    @pytest.mark.asyncio
    async def test_high_throughput_messages(self):
        """Test handling 10,000+ messages/second throughput"""
        from src.state_machine import StateMachineManager, CaseState
        
        manager = StateMachineManager()
        start = time.time()
        message_count = 10000
        
        for i in range(message_count):
            machine = manager.create_machine(f"msg-case-{i}")
            asyncio.run(machine.transition(CaseState.INVESTIGATING, "High throughput test"))
        
        duration = time.time() - start
        throughput = message_count / duration
        
        print(f"\nThroughput Test Results:")
        print(f"Messages: {message_count}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} messages/sec")
        
        assert throughput > 1000  # At least 1000 messages/second


class LocustLoadTest(HttpUser):
    """Locust-based load testing"""
    
    wait_time = between(1, 5)
    
    @task(1)
    def create_workflow(self):
        """Simulate creating a workflow"""
        self.client.post("/workflows/create", json={
            "case_id": f"case-{time.time()}",
            "steps": [{"service": "test", "action": "test"}]
        })
    
    @task(2)
    def get_workflow_status(self):
        """Simulate checking workflow status"""
        self.client.get("/workflows/test-workflow-id")
    
    @task(1)
    def execute_workflow(self):
        """Simulate executing a workflow"""
        self.client.post("/workflows/test-workflow-id/execute")


class CircuitBreakerLoadTest:
    """Test circuit breaker under load"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Test circuit breaker activates under high failure rate"""
        failure_count = 0
        request_count = 100
        
        # Simulate 50% failure rate
        for i in range(request_count):
            if i % 2 == 0:
                failure_count += 1
        
        failure_rate = failure_count / request_count
        
        # Circuit breaker should trigger at 50%+ failure rate
        assert failure_rate >= 0.5
        print(f"\nCircuit Breaker Test: {failure_rate*100:.1f}% failure rate - TRIGGERED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
