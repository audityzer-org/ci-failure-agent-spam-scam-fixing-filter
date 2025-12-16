"""Unit tests for OrchestrationEngine with Predictive Propositions."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from src.orchestration_engine import (
    OrchestrationEngine,
    Alert,
    AlertType,
    PredictiveProposition,
    PropositionDecision,
    PropositionLog,
    OrchestratorIntegration,
)


@pytest.fixture
def engine():
    """Create engine instance."""
    return OrchestrationEngine()


@pytest.fixture
def sample_alert():
    """Create sample CI failure alert."""
    return Alert(
        id="test-alert-1",
        type=AlertType.CI_FAILURE,
        description="Build failed: dependency resolution error",
        severity="high",
        timestamp=datetime.utcnow().isoformat(),
        source="jenkins",
        metadata={"build_id": "456", "branch": "main"}
    )


@pytest.fixture
def spam_alert():
    """Create sample spam incident alert."""
    return Alert(
        id="test-spam-1",
        type=AlertType.SPAM_INCIDENT,
        description="Suspicious email detected from external sender",
        severity="medium",
        timestamp=datetime.utcnow().isoformat(),
        source="email_gateway",
        metadata={"sender": "unknown@external.com", "subject": "Urgent: Update required"}
    )


@pytest.fixture
def scam_alert():
    """Create sample scam incident alert."""
    return Alert(
        id="test-scam-1",
        type=AlertType.SCAM_INCIDENT,
        description="Phishing attempt detected",
        severity="critical",
        timestamp=datetime.utcnow().isoformat(),
        source="security_scanner",
        metadata={"url": "http://fake-bank.com", "target_users": 150}
    )


@pytest.fixture
def sample_proposition():
    """Create sample proposition."""
    return PredictiveProposition(
        id="prop-1",
        title="Retry Failed Job",
        description="Automatically retry the failed CI job",
        action_type="auto_fix",
        parameters={"retry_count": 3},
        confidence_score=0.85,
        estimated_impact="2-5 minutes",
        priority=1
    )


class TestAlertProcessing:
    """Test alert processing functionality."""
    
    @pytest.mark.asyncio
    async def test_process_ci_failure_alert(self, engine, sample_alert):
        """Test processing a CI failure alert."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await engine.process_alert(sample_alert)
            
            assert result["status"] == "processed"
            assert result["alert_id"] == "test-alert-1"
            assert result["alert_type"] == "ci_failure"
            assert sample_alert.id in engine.active_alerts
            assert "request_id" in result
    
    @pytest.mark.asyncio
    async def test_process_spam_incident_alert(self, engine, spam_alert):
        """Test processing a spam incident alert."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await engine.process_alert(spam_alert)
            
            assert result["status"] == "processed"
            assert result["alert_type"] == "spam_incident"
            assert spam_alert.id in engine.active_alerts
    
    @pytest.mark.asyncio
    async def test_process_scam_incident_alert(self, engine, scam_alert):
        """Test processing a scam incident alert."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await engine.process_alert(scam_alert)
            
            assert result["status"] == "processed"
            assert result["alert_type"] == "scam_incident"
    
    @pytest.mark.asyncio
    async def test_close_alert(self, engine, sample_alert):
        """Test closing an alert."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            result = await engine.close_alert(sample_alert.id)
            
            assert result["status"] == "closed"
            assert sample_alert.id not in engine.active_alerts
    
    @pytest.mark.asyncio
    async def test_close_nonexistent_alert(self, engine):
        """Test closing an alert that doesn't exist."""
        result = await engine.close_alert("nonexistent-id")
        assert result["status"] == "error"


class TestPropositionTracking:
    """Test proposition decision tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_apply_proposition_accepted(self, engine, sample_alert, sample_proposition):
        """Test applying a proposition with user acceptance."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            request_id = "req-123"
            
            result = await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id=request_id,
                user_decision=PropositionDecision.ACCEPTED
            )
            
            assert result["proposition_id"] == "prop-1"
            assert result["user_decision"] == "accepted"
            assert result["status"] == "executed"
            assert len(engine.proposition_history) == 1
    
    @pytest.mark.asyncio
    async def test_apply_proposition_rejected(self, engine, sample_alert, sample_proposition):
        """Test applying a proposition with user rejection."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            request_id = "req-124"
            
            result = await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id=request_id,
                user_decision=PropositionDecision.REJECTED
            )
            
            assert result["user_decision"] == "rejected"
            assert result["status"] == "rejected"
            assert len(engine.proposition_history) == 1
    
    @pytest.mark.asyncio
    async def test_apply_proposition_ignored(self, engine, sample_alert, sample_proposition):
        """Test applying a proposition with user ignoring."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            request_id = "req-125"
            
            result = await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id=request_id,
                user_decision=PropositionDecision.IGNORED
            )
            
            assert result["user_decision"] == "ignored"
            assert len(engine.proposition_history) == 1
    
    @pytest.mark.asyncio
    async def test_proposition_logging_for_ml(self, engine, sample_alert, sample_proposition):
        """Test that proposition decisions are logged for ML training."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            request_id = "req-126"
            
            await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id=request_id,
                user_decision=PropositionDecision.ACCEPTED
            )
            
            logs = await engine.get_proposition_logs()
            assert len(logs) == 1
            
            log = logs[0]
            assert log.request_id == request_id
            assert log.alert_id == sample_alert.id
            assert log.proposition_id == sample_proposition.id
            assert log.user_decision == PropositionDecision.ACCEPTED
            assert log.presented_at is not None
            assert log.decision_timestamp is not None
    
    @pytest.mark.asyncio
    async def test_get_proposition_logs_filtering(self, engine, sample_alert, sample_proposition):
        """Test filtering proposition logs by alert_id."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            # Create two alerts
            alert2 = Alert(
                id="test-alert-2",
                type=AlertType.CI_FAILURE,
                description="Another build failed",
                severity="medium",
                timestamp=datetime.utcnow().isoformat(),
                source="jenkins",
                metadata={}
            )
            
            await engine.process_alert(sample_alert)
            await engine.process_alert(alert2)
            
            # Apply propositions to both
            await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id="req-1",
                user_decision=PropositionDecision.ACCEPTED
            )
            
            await engine.apply_proposition(
                alert_id=alert2.id,
                proposition=sample_proposition,
                request_id="req-2",
                user_decision=PropositionDecision.REJECTED
            )
            
            # Filter logs for first alert
            logs = await engine.get_proposition_logs(alert_id=sample_alert.id)
            assert len(logs) == 1
            assert logs[0].alert_id == sample_alert.id


class TestSecurityIncidentHandling:
    """Test spam/scam incident handling."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration_process_ci_failure(self, sample_alert):
        """Test OrchestratorIntegration for CI failure."""
        integration = OrchestratorIntegration()
        
        failure_data = {
            "id": "ci-fail-1",
            "description": "Test compilation failed",
            "severity": "high",
            "source": "github_actions",
            "metadata": {"workflow": "build.yml"}
        }
        
        with patch.object(integration.engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            result = await integration.engine.process_alert(
                Alert(
                    id=failure_data["id"],
                    type=AlertType.CI_FAILURE,
                    description=failure_data["description"],
                    severity=failure_data["severity"],
                    timestamp=datetime.utcnow().isoformat(),
                    source=failure_data["source"],
                    metadata=failure_data["metadata"]
                )
            )
            
            assert result["alert_type"] == "ci_failure"
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration_process_security_incident(self, spam_alert):
        """Test OrchestratorIntegration for security incident."""
        integration = OrchestratorIntegration()
        
        incident_data = {
            "id": "sec-inc-1",
            "incident_type": "spam_incident",
            "description": "Spam email detected",
            "severity": "medium",
            "source": "email_security",
            "metadata": {"sender_domain": "unknown.com"}
        }
        
        with patch.object(integration.engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            result = await integration.engine.process_alert(
                Alert(
                    id=incident_data["id"],
                    type=AlertType.SPAM_INCIDENT,
                    description=incident_data["description"],
                    severity=incident_data["severity"],
                    timestamp=datetime.utcnow().isoformat(),
                    source=incident_data["source"],
                    metadata=incident_data["metadata"]
                )
            )
            
            assert result["alert_type"] == "spam_incident"


class TestAlertSummary:
    """Test alert summary functionality."""
    
    @pytest.mark.asyncio
    async def test_get_alert_summary(self, engine, sample_alert, spam_alert, sample_proposition):
        """Test getting alert summary with mixed alert types."""
        with patch.object(engine, '_fetch_predictive_propositions', new_callable=AsyncMock):
            await engine.process_alert(sample_alert)
            await engine.process_alert(spam_alert)
            
            # Apply proposition to track it
            await engine.apply_proposition(
                alert_id=sample_alert.id,
                proposition=sample_proposition,
                request_id="req-sum",
                user_decision=PropositionDecision.ACCEPTED
            )
            
            summary = await engine.get_alert_summary()
            
            assert summary["total_active"] == 2
            assert summary["alert_types"]["ci_failure"] == 1
            assert summary["alert_types"]["spam_incident"] == 1
            assert summary["total_propositions_tracked"] == 1
            assert summary["total_actions_executed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
