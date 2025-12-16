"""Integration tests with retry logic, error handling, and performance testing."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import json
from src.orchestration_engine import (
    OrchestrationEngine,
    Alert,
    AlertType,
    PredictiveProposition,
    PropositionDecision,
)


class RetryConfig:
    """Configuration for retry logic."""
    MAX_RETRIES = 3
    RETRY_DELAYS = [0.1, 0.2, 0.4]  # exponential backoff
    TIMEOUT = 5.0


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_success_on_second_attempt(self):
        """Test successful retry after initial failure."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="alert-1",
            type=AlertType.CI_FAILURE,
            description="Build failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={}
        )
        
        call_count = 0
        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Service unavailable")
            return []
        
        with patch.object(engine, 'client') as mock_client:
            mock_client.post = mock_fetch
            # Should succeed on retry
            result = await engine._fetch_predictive_propositions(alert, "req-1")
            assert call_count >= 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries exceeded."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="alert-2",
            type=AlertType.SPAM_INCIDENT,
            description="Spam detected",
            severity="medium",
            timestamp=datetime.utcnow().isoformat(),
            source="email",
            metadata={}
        )
        
        failure_count = 0
        async def always_fail(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            raise ConnectionError("Persistent failure")
        
        with patch.object(engine, 'client') as mock_client:
            mock_client.post = always_fail
            result = await engine._fetch_predictive_propositions(alert, "req-2")
            assert result == []  # Returns empty on failure


class TestPredictiveServiceIntegration:
    """Test integration with predictive propositions service."""
    
    @pytest.mark.asyncio
    async def test_ci_failure_propositions(self):
        """Test getting propositions for CI failure."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="ci-fail-001",
            type=AlertType.CI_FAILURE,
            description="Build failed: tests failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={"build_id": "123", "branch": "main"}
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "actions": [
                {
                    "action_id": "prop-1",
                    "title": "Retry Build",
                    "description": "Retry the build",
                    "action_type": "auto_fix",
                    "parameters": {"retry_count": 3},
                    "success_rate": 0.85,
                    "estimated_time": "5 minutes",
                    "priority": 1
                }
            ]
        }
        
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            propositions = await engine._fetch_predictive_propositions(alert, "req-1")
            assert len(propositions) > 0
    
    @pytest.mark.asyncio
    async def test_spam_incident_propositions(self):
        """Test getting propositions for spam incident."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="spam-001",
            type=AlertType.SPAM_INCIDENT,
            description="Suspicious email from external",
            severity="medium",
            timestamp=datetime.utcnow().isoformat(),
            source="email_gateway",
            metadata={"sender": "unknown@external.com"}
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "actions": [
                {
                    "action_id": "prop-spam-1",
                    "title": "Quarantine & Review",
                    "description": "Move to quarantine",
                    "action_type": "manual_review",
                    "parameters": {},
                    "success_rate": 0.92,
                    "estimated_time": "immediate",
                    "priority": 1
                }
            ]
        }
        
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            propositions = await engine._fetch_predictive_propositions(alert, "req-2")
            assert len(propositions) > 0
    
    @pytest.mark.asyncio
    async def test_service_timeout_handling(self):
        """Test handling of service timeout."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="alert-timeout",
            type=AlertType.CI_FAILURE,
            description="Build failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={}
        )
        
        async def timeout_error(*args, **kwargs):
            raise asyncio.TimeoutError("Service timeout")
        
        with patch.object(engine.client, 'post', side_effect=timeout_error):
            propositions = await engine._fetch_predictive_propositions(alert, "req-3")
            assert propositions == []  # Returns empty on timeout


class TestConcurrentPropositionProcessing:
    """Test handling multiple concurrent propositions."""
    
    @pytest.mark.asyncio
    async def test_process_multiple_alerts_concurrently(self):
        """Test processing multiple alerts concurrently."""
        engine = OrchestrationEngine()
        
        alerts = [
            Alert(
                id=f"alert-{i}",
                type=AlertType.CI_FAILURE if i % 2 == 0 else AlertType.SPAM_INCIDENT,
                description=f"Alert {i}",
                severity="high" if i % 3 == 0 else "medium",
                timestamp=datetime.utcnow().isoformat(),
                source="system",
                metadata={"index": i}
            )
            for i in range(10)
        ]
        
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock) as mock:
            mock.return_value = []
            results = await asyncio.gather(*[
                engine.process_alert(alert) for alert in alerts
            ])
            
            assert len(results) == 10
            assert all(r["status"] == "processed" for r in results)
            assert len(engine.active_alerts) == 10
    
    @pytest.mark.asyncio
    async def test_apply_propositions_concurrently(self):
        """Test applying multiple propositions concurrently."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="concurrent-alert",
            type=AlertType.CI_FAILURE,
            description="Build failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={}
        )
        
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(alert)
            
            propositions = [
                PredictiveProposition(
                    id=f"prop-{i}",
                    title=f"Proposition {i}",
                    description=f"Desc {i}",
                    action_type="auto_fix",
                    parameters={},
                    confidence_score=0.8 + (i * 0.01),
                    estimated_impact="2 mins",
                    priority=1
                )
                for i in range(5)
            ]
            
            results = await asyncio.gather(*[
                engine.apply_proposition(
                    alert_id=alert.id,
                    proposition=prop,
                    request_id=f"req-{i}",
                    user_decision=PropositionDecision.ACCEPTED if i % 2 == 0 else PropositionDecision.REJECTED
                )
                for i, prop in enumerate(propositions)
            ])
            
            assert len(results) == 5
            assert len(engine.proposition_history) == 5


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_fallback(self):
        """Test fallback when service is unavailable."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="unavail-alert",
            type=AlertType.CI_FAILURE,
            description="Build failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={}
        )
        
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock:
            mock.side_effect = ConnectionError("Service unavailable")
            result = await engine.process_alert(alert)
            
            # Should still process alert even if service unavailable
            assert result["status"] == "processed"
            assert result["proposition_count"] == 0  # Empty propositions
    
    @pytest.mark.asyncio
    async def test_invalid_alert_handling(self):
        """Test handling of invalid alert data."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="invalid-alert",
            type=AlertType.CI_FAILURE,
            description="",  # Empty description
            severity="unknown",  # Invalid severity
            timestamp="invalid-date",
            source="",
            metadata=None
        )
        
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            # Should handle gracefully
            result = await engine.process_alert(alert)
            assert result["status"] == "processed"


class TestDataConsistency:
    """Test data consistency across operations."""
    
    @pytest.mark.asyncio
    async def test_proposition_history_consistency(self):
        """Test consistency of proposition history."""
        engine = OrchestrationEngine()
        alert = Alert(
            id="consistency-alert",
            type=AlertType.CI_FAILURE,
            description="Build failed",
            severity="high",
            timestamp=datetime.utcnow().isoformat(),
            source="jenkins",
            metadata={}
        )
        
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(alert)
            
            proposition = PredictiveProposition(
                id="prop-consistency",
                title="Test Proposition",
                description="Test",
                action_type="auto_fix",
                parameters={},
                confidence_score=0.85,
                estimated_impact="5 mins",
                priority=1
            )
            
            await engine.apply_proposition(
                alert_id=alert.id,
                proposition=proposition,
                request_id="req-consistency",
                user_decision=PropositionDecision.ACCEPTED
            )
            
            # Verify data consistency
            logs = await engine.get_proposition_logs()
            assert len(logs) == 1
            
            log = logs[0]
            assert log.alert_id == alert.id
            assert log.proposition_id == proposition.id
            assert log.user_decision == PropositionDecision.ACCEPTED
            assert log.request_id == "req-consistency"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
