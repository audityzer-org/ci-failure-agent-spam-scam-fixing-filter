"""Unit tests for OrchestrationEngine."""

import pytest
from unittest.mock import AsyncMock, patch
from src.orchestration_engine import (
    OrchestrationEngine,
    Alert,
    AlertType,
    PredictiveAction,
)


@pytest.fixture
def engine():
    """Create engine instance."""
    return OrchestrationEngine()


@pytest.fixture
def sample_alert():
    """Create sample alert."""
    return Alert(
        id="test-alert-1",
        type=AlertType.CI_FAILURE,
        description="Build failed",
        severity="high",
        timestamp="2025-12-14T19:00:00Z",
        source="jenkins",
        metadata={"build_id": "456"}
    )


@pytest.mark.asyncio
async def test_process_alert(engine, sample_alert):
    """Test alert processing."""
    with patch.object(engine, '_fetch_predictive_actions', new_callable=AsyncMock) as mock:
        mock.return_value = []
        result = await engine.process_alert(sample_alert)
        
        assert result["status"] == "processed"
        assert result["alert_id"] == "test-alert-1"
        assert sample_alert.id in engine.active_alerts


@pytest.mark.asyncio
async def test_close_alert(engine, sample_alert):
    """Test closing an alert."""
    with patch.object(engine, '_fetch_predictive_actions', new_callable=AsyncMock):
        await engine.process_alert(sample_alert)
        result = await engine.close_alert(sample_alert.id)
        
        assert result["status"] == "closed"
        assert sample_alert.id not in engine.active_alerts


@pytest.mark.asyncio
async def test_execute_action_approved(engine, sample_alert):
    """Test executing approved action."""
    with patch.object(engine, '_fetch_predictive_actions', new_callable=AsyncMock):
        await engine.process_alert(sample_alert)
        
        action = PredictiveAction(
            id="action-1",
            title="Retry",
            description="Retry build",
            action_type="auto_remediation",
            parameters={},
            confidence_score=0.9,
            estimated_impact="low"
        )
        
        result = await engine.execute_action(
            sample_alert.id,
            action,
            user_decision=True
        )
        
        assert result["user_approved"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
