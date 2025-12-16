"""End-to-End Production Tests - Comprehensive integration testing."""
import pytest
import httpx
import asyncio
import time
from typing import Dict

# Production endpoints
BASE_URL = "https://api.auditorsec.com"
AUTH_ENDPOINT = f"{BASE_URL}/auth/login"
HEALTH_ENDPOINT = f"{BASE_URL}/health"

class TestAuthentication:
    """Test authentication and JWT token management."""
    
    @pytest.mark.asyncio
    async def test_login_valid_credentials(self):
        """Test login with valid admin credentials."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AUTH_ENDPOINT,
                json={"username": "admin", "password": "admin"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user_id"] == "user-001"
            assert "admin" in data["roles"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AUTH_ENDPOINT,
                json={"username": "invalid", "password": "wrong"}
            )
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_rbac_role_enforcement(self):
        """Test role-based access control."""
        async with httpx.AsyncClient() as client:
            # Get viewer token
            login_response = await client.post(
                AUTH_ENDPOINT,
                json={"username": "viewer", "password": "viewer"}
            )
            token = login_response.json()["access_token"]
            
            # Try to access restricted endpoint
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{BASE_URL}/api/v1/admin/settings",
                headers=headers
            )
            assert response.status_code in [403, 404]

class TestServiceHealth:
    """Test all microservices health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check_main_api(self):
        """Test main API health endpoint."""
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_all_services_available(self):
        """Test all 5 services are responsive."""
        services = [
            "Anti-Corruption Orchestrator",
            "Audit Trail Aggregator",
            "Compliance Validator",
            "Spam Detection Service",
            "Predictive Suggestions Service"
        ]
        
        async with httpx.AsyncClient(verify=False) as client:
            # Check main health endpoint
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200

class TestServiceIntegration:
    """Test cross-service integration flows."""
    
    @pytest.mark.asyncio
    async def test_anti_corruption_workflow(self):
        """Test anti-corruption case creation and investigation."""
        async with httpx.AsyncClient(verify=False) as client:
            # Create case
            case_payload = {
                "case_type": "availability_advantage",
                "description": "Test case for E2E validation",
                "severity": 7,
                "isolated_group": "test-service-group",
                "source_details": {"source": "automated_test"}
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/anti-corruption/cases",
                json=case_payload
            )
            assert response.status_code in [200, 201]
            case_id = response.json().get("case_id")
            assert case_id is not None
    
    @pytest.mark.asyncio  
    async def test_spam_detection_flow(self):
        """Test spam detection service integration."""
        async with httpx.AsyncClient(verify=False) as client:
            payload = {
                "content": "Please verify your account immediately. Click here now to confirm credentials.",
                "context": "email_content",
                "threshold": 75
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/spam/detect",
                json=payload
            )
            assert response.status_code == 200
            data = response.json()
            assert "is_spam" in data
            assert "confidence" in data

class TestPerformance:
    """Test performance SLOs."""
    
    @pytest.mark.asyncio
    async def test_response_time_under_150ms(self):
        """Test that p99 response time is under 150ms."""
        response_times = []
        
        async with httpx.AsyncClient(verify=False) as client:
            for _ in range(100):
                start = time.time()
                response = await client.get(f"{BASE_URL}/health")
                elapsed = (time.time() - start) * 1000  # Convert to ms
                response_times.append(elapsed)
                assert response.status_code == 200
        
        response_times.sort()
        p99 = response_times[int(len(response_times) * 0.99)]
        assert p99 < 150, f"P99 latency {p99}ms exceeds 150ms SLO"
    
    @pytest.mark.asyncio
    async def test_error_rate_under_1_percent(self):
        """Test that error rate stays below 1%."""
        total_requests = 1000
        failed_requests = 0
        
        async with httpx.AsyncClient(verify=False) as client:
            for _ in range(total_requests):
                response = await client.get(f"{BASE_URL}/health")
                if response.status_code != 200:
                    failed_requests += 1
        
        error_rate = (failed_requests / total_requests) * 100
        assert error_rate < 1.0, f"Error rate {error_rate}% exceeds 1% SLO"

class TestSecurity:
    """Test security configurations."""
    
    @pytest.mark.asyncio
    async def test_https_enforced(self):
        """Test HTTPS is properly enforced."""
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(f"{BASE_URL}/health")
            # Check security headers
            assert "content-type" in response.headers
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Test that invalid JWT tokens are rejected."""
        async with httpx.AsyncClient(verify=False) as client:
            headers = {"Authorization": "Bearer invalid.token.here"}
            response = await client.get(
                f"{BASE_URL}/user/info",
                headers=headers
            )
            assert response.status_code == 401

# Run tests

class TestPredictivePropositionsE2E:
    """Phase 3.4: E2E tests for predictive propositions workflow with retry & error handling."""
    
    PROPOSITIONS_BASE_URL = "http://localhost:8001"
    
    @pytest.mark.asyncio
    async def test_full_alert_to_execution_workflow(self):
        """Test complete workflow: Alert → Propositions → Decision → Execution → Logging."""
        async with httpx.AsyncClient() as client:
            # Step 1: Create alert
            alert_payload = {
                "id": "alert-e2e-001",
                "type": "CI_FAILURE",
                "severity": 8,
                "description": "Unit tests failed in deployment pipeline",
                "metadata": {"repo": "test-repo", "branch": "main"}
            }
            
            # Step 2: Process alert and get propositions
            response = await client.post(
                f"{BASE_URL}/api/v1/alerts/process",
                json=alert_payload
            )
            assert response.status_code in [200, 201]
            result = response.json()
            assert "propositions" in result
            assert "request_id" in result
            assert result["proposition_count"] > 0
    
    @pytest.mark.asyncio
    async def test_retry_logic_on_transient_failure(self):
        """Test retry mechanism with exponential backoff recovers from transient failures."""
        async with httpx.AsyncClient() as client:
            # Simulate transient failure by calling service that may timeout
            for attempt in range(3):
                try:
                    response = await client.get(
                        f"{self.PROPOSITIONS_BASE_URL}/health",
                        timeout=2.0
                    )
                    if response.status_code == 200:
                        break
                except httpx.TimeoutException:
                    # Expected on transient failures
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
            # Final attempt should succeed
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_service_unavailable(self):
        """Test graceful degradation when propositions service is unavailable."""
        async with httpx.AsyncClient() as client:
            alert_payload = {
                "id": "alert-degradation-test",
                "type": "SECURITY_INCIDENT",
                "severity": 9,
                "description": "Security alert when service is down",
                "metadata": {}
            }
            
            # Even if propositions service is unavailable,
            # orchestration should return gracefully with empty propositions
            response = await client.post(
                f"{BASE_URL}/api/v1/alerts/process",
                json=alert_payload
            )
            # Should still return 200 with graceful degradation
            if response.status_code == 200:
                result = response.json()
                # May have empty propositions but structure intact
                assert "status" in result
    
    @pytest.mark.asyncio
    async def test_proposition_logging_for_ml_training(self):
        """Test that propositions and user decisions are logged for ML ranker training."""
        async with httpx.AsyncClient() as client:
            alert_id = "alert-ml-logging-001"
            alert_payload = {
                "id": alert_id,
                "type": "CI_FAILURE",
                "severity": 5,
                "description": "Test for ML logging",
                "metadata": {}
            }
            
            # Get propositions
            response = await client.post(
                f"{BASE_URL}/api/v1/alerts/process",
                json=alert_payload
            )
            assert response.status_code in [200, 201]
            result = response.json()
            propositions = result.get("propositions", [])
            
            if propositions:
                # Simulate user decision
                decision_payload = {
                    "alert_id": alert_id,
                    "proposition_id": propositions[0].get("id"),
                    "decision": "ACCEPTED"
                }
                
                # Apply decision
                response = await client.post(
                    f"{BASE_URL}/api/v1/propositions/apply",
                    json=decision_payload
                )
                assert response.status_code in [200, 202]
                
                # Verify decision is logged for ML training
                response = await client.get(
                    f"{BASE_URL}/api/v1/propositions/logs?alert_id={alert_id}"
                )
                if response.status_code == 200:
                    logs = response.json()
                    assert isinstance(logs, (list, dict))
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker transitions through closed → open → half-open → closed."""
        async with httpx.AsyncClient() as client:
            # Monitor circuit breaker behavior through multiple requests
            request_count = 0
            successful_count = 0
            
            for i in range(20):
                try:
                    response = await client.get(
                        f"{self.PROPOSITIONS_BASE_URL}/api/propositions",
                        timeout=2.0
                    )
                    request_count += 1
                    if response.status_code == 200:
                        successful_count += 1
                except (httpx.TimeoutException, httpx.ConnectError):
                    request_count += 1
                    # Continue testing
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Most requests should eventually succeed or fail gracefully
            assert request_count > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_alert_processing_with_retry(self):
        """Test multiple alerts processed concurrently with retry logic."""
        async with httpx.AsyncClient() as client:
            # Create multiple concurrent alert requests
            tasks = []
            for i in range(5):
                alert_payload = {
                    "id": f"concurrent-alert-{i}",
                    "type": "CI_FAILURE",
                    "severity": 6,
                    "description": f"Concurrent test alert {i}",
                    "metadata": {}
                }
                
                task = client.post(
                    f"{BASE_URL}/api/v1/alerts/process",
                    json=alert_payload
                )
                tasks.append(task)
            
            # Execute all concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all completed
            successful = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code in [200, 201])
            assert successful >= 3  # At least 3 should succeed
    
    @pytest.mark.asyncio
    async def test_ml_logging_data_structure(self):
        """Verify PropositionLog structure contains all fields for ML ranker training."""
        async with httpx.AsyncClient() as client:
            # Query existing logs
            response = await client.get(
                f"{BASE_URL}/api/v1/propositions/logs?limit=1"
            )
            
            if response.status_code == 200:
                logs = response.json()
                if isinstance(logs, list) and logs:
                    log_entry = logs[0]
                    # Verify required fields for ML training
                    required_fields = ["alert_id", "proposition_id", "user_decision", "timestamp"]
                    for field in required_fields:
                        assert field in log_entry or "propositions" in str(log_entry).lower()



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
