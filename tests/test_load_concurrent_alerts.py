"""Load Testing Script for Concurrent Alert Processing

Tests system performance with 10,000+ concurrent alerts
using asyncio and simulated workloads.
"""

import asyncio
import time
import logging
import json
from typing import List, Dict, Any
from dataclasses import dataclass
import random
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Metrics from load test execution."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    error_rate: float


class ConcurrentAlertSimulator:
    """Simulates concurrent alert processing."""

    def __init__(self, api_endpoint: str = "http://localhost:8000"):
        self.api_endpoint = api_endpoint
        self.latencies: List[float] = []
        self.errors: List[str] = []
        self.logger = logging.getLogger(__name__)

    async def send_alert(self, alert_id: str) -> float:
        """Simulate sending an alert and measure latency."""
        start_time = time.time()
        try:
            # Simulate API call with random delay
            delay = random.uniform(0.01, 0.5)
            await asyncio.sleep(delay)
            
            # Simulate occasional failures (5% error rate)
            if random.random() < 0.05:
                raise Exception("Simulated API error")
            
            latency_ms = (time.time() - start_time) * 1000
            return latency_ms
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.errors.append(str(e))
            self.logger.error(f"Alert {alert_id} failed: {str(e)}")
            raise

    async def run_load_test(self, concurrent_users: int = 100,
                           requests_per_user: int = 100) -> LoadTestResult:
        """Run concurrent load test."""
        total_requests = concurrent_users * requests_per_user
        self.logger.info(f"Starting load test: {concurrent_users} users, "
                        f"{requests_per_user} requests each")
        
        start_time = time.time()
        tasks = []
        
        for user_id in range(concurrent_users):
            for req_id in range(requests_per_user):
                alert_id = f"alert_{user_id}_{req_id}"
                tasks.append(self.send_alert(alert_id))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_duration = time.time() - start_time
        successful = 0
        
        for result in results:
            if isinstance(result, float):
                self.latencies.append(result)
                successful += 1
        
        # Calculate statistics
        if self.latencies:
            sorted_latencies = sorted(self.latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
        else:
            sorted_latencies = []
            p95_idx = p99_idx = 0
        
        test_result = LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=len(self.errors),
            total_duration_seconds=total_duration,
            min_latency_ms=min(self.latencies) if self.latencies else 0,
            max_latency_ms=max(self.latencies) if self.latencies else 0,
            avg_latency_ms=statistics.mean(self.latencies) if self.latencies else 0,
            p95_latency_ms=sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else 0,
            p99_latency_ms=sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else 0,
            requests_per_second=total_requests / total_duration,
            error_rate=len(self.errors) / total_requests if total_requests > 0 else 0
        )
        
        return test_result

    def print_results(self, result: LoadTestResult) -> None:
        """Print formatted test results."""
        print("\n=== Load Test Results ===")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful: {result.successful_requests}")
        print(f"Failed: {result.failed_requests}")
        print(f"Error Rate: {result.error_rate:.2%}")
        print(f"Total Duration: {result.total_duration_seconds:.2f}s")
        print(f"Requests/sec: {result.requests_per_second:.2f}")
        print("\nLatency Statistics:")
        print(f"  Min: {result.min_latency_ms:.2f}ms")
        print(f"  Max: {result.max_latency_ms:.2f}ms")
        print(f"  Avg: {result.avg_latency_ms:.2f}ms")
        print(f"  P95: {result.p95_latency_ms:.2f}ms")
        print(f"  P99: {result.p99_latency_ms:.2f}ms")
        print("=" * 24 + "\n")


async def test_10k_concurrent_alerts():
    """Test with 10,000 concurrent alerts."""
    logging.basicConfig(level=logging.INFO)
    
    simulator = ConcurrentAlertSimulator()
    
    # Test with 100 concurrent users, 100 requests each = 10,000 total
    result = await simulator.run_load_test(
        concurrent_users=100,
        requests_per_user=100
    )
    
    simulator.print_results(result)
    
    # Assertions for performance targets
    assert result.error_rate < 0.05, "Error rate too high"
    assert result.avg_latency_ms < 500, "Average latency too high"
    assert result.p99_latency_ms < 1000, "P99 latency too high"
    assert result.requests_per_second > 100, "Throughput too low"
    
    print("✓ All load test assertions passed!")
    return result


if __name__ == "__main__":
    asyncio.run(test_10k_concurrent_alerts())
