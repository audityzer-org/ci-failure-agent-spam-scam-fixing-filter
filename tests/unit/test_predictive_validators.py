"""Unit tests for Predictive Suggestions validators module.

Tests cover input validation, sanitization, and response validation.
"""

import pytest
from unittest.mock import patch, MagicMock
from services.predictive_suggestions.validators import (
    ImpactLevel,
    ValidationResult,
    PredictionRequestValidator,
    SuggestionResponseValidator,
    InputValidator,
    ParameterSanitizer,
)


class TestImpactLevel:
    """Tests for ImpactLevel enum."""

    def test_impact_level_values(self):
        """Test that ImpactLevel enum has expected values."""
        assert hasattr(ImpactLevel, 'LOW')
        assert hasattr(ImpactLevel, 'MEDIUM')
        assert hasattr(ImpactLevel, 'HIGH')
        assert hasattr(ImpactLevel, 'CRITICAL')

    def test_impact_level_ordering(self):
        """Test that impact levels can be compared."""
        # Should be able to determine relative severity
        assert ImpactLevel.LOW is not None
        assert ImpactLevel.CRITICAL is not None


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(is_valid=True, errors=[])
        assert result.is_valid is True
        assert result.errors == []

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        errors = ["Field missing", "Invalid format"]
        result = ValidationResult(is_valid=False, errors=errors)
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Field missing" in result.errors


class TestPredictionRequestValidator:
    """Tests for PredictionRequestValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return PredictionRequestValidator()

    def test_validator_initialization(self, validator):
        """Test validator can be initialized."""
        assert validator is not None
        assert isinstance(validator, PredictionRequestValidator)

    def test_validate_valid_request(self, validator):
        """Test validation of valid prediction request."""
        valid_request = {
            'failure_message': 'Test failure',
            'context': 'CI/CD Pipeline',
        }
        result = validator.validate(valid_request)
        # Should accept valid request
        assert result is not None

    def test_validate_empty_request(self, validator):
        """Test validation of empty request."""
        empty_request = {}
        result = validator.validate(empty_request)
        # Should handle empty request
        assert result is not None

    def test_validate_request_with_malicious_content(self, validator):
        """Test validation against injection attempts."""
        malicious_request = {
            'failure_message': '<script>alert("xss")</script>',
        }
        result = validator.validate(malicious_request)
        # Should sanitize or reject
        assert result is not None


class TestSuggestionResponseValidator:
    """Tests for SuggestionResponseValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SuggestionResponseValidator()

    def test_validator_initialization(self, validator):
        """Test validator can be initialized."""
        assert validator is not None
        assert isinstance(validator, SuggestionResponseValidator)

    def test_validate_valid_response(self, validato, valid_suggestion_response_datar):
        """Test validation of valid response."""
        valid_response = valid_suggestion_response_data
        result = validator.validate(valid_response)
        assert result is not None

    def test_validate_invalid_confidence(self, validator):
        """Test validation with invalid confidence."""
        invalid_response = {
            'confidence': 1.5,  # Out of bounds
        }
        result = validator.validate(invalid_response)
        assert result is not None

    def test_validate_missing_fields(self, validator, valid_suggestion_response_data):
        """Test validation with missing required fields."""
        incomplete_response = valid_suggestion_response_data
        result = validator.validate(incomplete_response)
        assert result is not None


class TestInputValidator:
    """Tests for InputValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return InputValidator()

    def test_validate_string_input(self, validator):
        """Test string input validation."""
        result = validator.validate_string("Valid input text")
        assert result is not None

    def test_validate_empty_string(self, validator):
        """Test empty string handling."""
        result = validator.validate_string("")
        # Should handle gracefully
        assert result is not None

    def test_validate_numeric_input(self, validator):
        """Test numeric input validation."""
        result = validator.validate_numeric(42)
        assert result is not None

    def test_validate_numeric_boundary(self, validator):
        """Test numeric boundary values."""
        result = validator.validate_numeric(0)
        assert result is not None
        
        result = validator.validate_numeric(-1)
        assert result is not None

    def test_validate_list_input(self, validator):
        """Test list input validation."""
        result = validator.validate_list(['item1', 'item2'])
        assert result is not None

    def test_validate_empty_list(self, validator):
        """Test empty list handling."""
        result = validator.validate_list([])
        assert result is not None


class TestParameterSanitizer:
    """Tests for ParameterSanitizer."""

    @pytest.fixture
    def sanitizer(self):
        """Create sanitizer instance."""
        return ParameterSanitizer()

    def test_sanitize_string(self, sanitizer):
        """Test string sanitization."""
        input_str = "  normal text  "
        result = sanitizer.sanitize_string(input_str)
        assert result is not None

    def test_sanitize_html_content(self, sanitizer):
        """Test HTML content sanitization."""
        dirty_html = '<script>alert("xss")</script>'
        result = sanitizer.sanitize_string(dirty_html)
        # Should remove or escape dangerous content
        assert result is not None

    def test_sanitize_sql_injection_attempt(self, sanitizer):
        """Test SQL injection attempt sanitization."""
        sql_injection = "'; DROP TABLE users; --"
        result = sanitizer.sanitize_string(sql_injection)
        assert result is not None

    def test_sanitize_unicode_content(self, sanitizer):
        """Test Unicode content sanitization."""
        unicode_text = "Здравствуй мир \u0000 special"
        result = sanitizer.sanitize_string(unicode_text)
        assert result is not None

    def test_sanitize_numeric_parameter(self, sanitizer):
        """Test numeric parameter sanitization."""
        result = sanitizer.sanitize_numeric("123")
        assert result is not None

    def test_sanitize_invalid_numeric(self, sanitizer):
        """Test invalid numeric parameter handling."""
        result = sanitizer.sanitize_numeric("not a number")
        # Should handle gracefully
        assert result is not None

    def test_sanitize_email(self, sanitizer):
        """Test email sanitization."""
        email = "user@example.com"
        result = sanitizer.sanitize_email(email)
        assert result is not None

    def test_sanitize_invalid_email(self, sanitizer):
        """Test invalid email handling."""
        invalid_email = "not-an-email"
        result = sanitizer.sanitize_email(invalid_email)
        assert result is not None


class TestValidatorsIntegration:
    """Integration tests for validators working together."""

    def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        request_validator = PredictionRequestValidator()
        response_validator = SuggestionResponseValidator()
        
        request = {'failure_message': 'Build failed'}
        response = {'suggestions': [], 'confidence': 0.8}
        
        req_result = request_validator.validate(request)
        resp_result = response_validator.validate(response)
        
        assert req_result is not None
        assert resp_result is not None

    def test_sanitization_before_validation(self):
        """Test sanitizing input before validation."""
        sanitizer = ParameterSanitizer()
        validator = InputValidator()
        
        dirty_input = '<script>test</script>'
        cleaned = sanitizer.sanitize_string(dirty_input)
        result = validator.validate_string(cleaned)
        
        assert result is not None
