"""Tests for predictive suggestions engine."""

import pytest
from src.predictive_suggestions import SuggestionEngine, SuggestionType


class TestSuggestionEngine:
    """Test SuggestionEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = SuggestionEngine()
    
    def test_generate_suggestions_ci_failure(self):
        """Test generating suggestions for CI failure."""
        alert_text = "AssertionError: Expected value 42 but got 41"
        suggestions = self.engine.generate_suggestions(
            alert_text=alert_text,
            alert_type="CI_FAILURE",
            confidence_threshold=0.7
        )
        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.TEST_FAILURE_FIX
        assert suggestions[0].confidence >= 0.7
    
    def test_generate_suggestions_build_error(self):
        """Test generating suggestions for build error."""
        alert_text = "SyntaxError: invalid syntax in module.py line 42"
        suggestions = self.engine.generate_suggestions(
            alert_text=alert_text,
            alert_type="CI_FAILURE"
        )
        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.BUILD_ERROR_FIX
        assert suggestions[0].confidence > 0.95
    
    def test_generate_suggestions_security_phishing(self):
        """Test generating suggestions for phishing alert."""
        alert_text = "Suspicious email: Please verify your account credentials immediately"
        suggestions = self.engine.generate_suggestions(
            alert_text=alert_text,
            alert_type="SECURITY_INCIDENT"
        )
        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.PHISHING_ALERT
    
    def test_generate_suggestions_scam(self):
        """Test generating suggestions for scam detection."""
        alert_text = "You have won a prize! Wire $500 to claim your lottery winnings"
        suggestions = self.engine.generate_suggestions(
            alert_text=alert_text,
            alert_type="SECURITY_INCIDENT"
        )
        assert len(suggestions) > 0
        assert suggestions[0].type == SuggestionType.SCAM_DETECTION
    
    def test_rank_suggestions(self):
        """Test ranking suggestions by confidence and severity."""
        alert_text = "AssertionError and phishing attempt"
        suggestions = self.engine.generate_suggestions(alert_text, "MIXED")
        ranked = self.engine.rank_suggestions(suggestions)
        assert len(ranked) > 0
        # Critical should rank higher than medium
        for i in range(len(ranked) - 1):
            assert ranked[i].confidence * (1.0 if ranked[i].severity == 'critical' else 0.5) >= \
                   ranked[i + 1].confidence * (1.0 if ranked[i + 1].severity == 'critical' else 0.5)
    
    def test_filter_suggestions_by_severity(self):
        """Test filtering suggestions by severity."""
        alert_text = "phishing and build error"
        suggestions = self.engine.generate_suggestions(alert_text, "MIXED")
        critical = self.engine.filter_suggestions(
            suggestions,
            severity='critical'
        )
        assert all(s.severity == 'critical' for s in critical)
    
    def test_filter_suggestions_by_confidence(self):
        """Test filtering suggestions by confidence threshold."""
        alert_text = "timeout occurred"
        suggestions = self.engine.generate_suggestions(alert_text, "CI_FAILURE")
        high_conf = self.engine.filter_suggestions(
            suggestions,
            min_confidence=0.9
        )
        assert all(s.confidence >= 0.9 for s in high_conf)
    
    def test_batch_generate_suggestions(self):
        """Test batch generation of suggestions."""
        alerts = [
            {"id": "1", "text": "AssertionError", "type": "CI_FAILURE"},
            {"id": "2", "text": "phishing", "type": "SECURITY"},
            {"id": "3", "text": "timeout", "type": "CI_FAILURE"}
        ]
        results = self.engine.batch_generate_suggestions(alerts)
        assert len(results) == 3
        assert all(isinstance(v, list) for v in results.values())
    
    def test_no_suggestions_for_unknown_alert(self):
        """Test that unknown alerts produce no suggestions."""
        alert_text = "This is a random message with no patterns"
        suggestions = self.engine.generate_suggestions(
            alert_text=alert_text,
            alert_type="UNKNOWN",
            confidence_threshold=0.9
        )
        assert len(suggestions) == 0 or suggestions[0].confidence < 0.9
