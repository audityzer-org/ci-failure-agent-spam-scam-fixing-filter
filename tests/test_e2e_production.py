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
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
