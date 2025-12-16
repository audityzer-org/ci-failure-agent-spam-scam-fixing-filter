"""Input validation and sanitization module for Predictive Suggestions Service."""
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator, ValidationError
from enum import Enum


class ImpactLevel(str, Enum):
    """Enum for impact levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationResult(BaseModel):
    """Result of validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PredictionRequestValidator(BaseModel):
    """Validator for prediction requests."""
    failure_pattern: str = Field(..., min_length=1, max_length=500)
    historical_data: Dict[str, Any] = Field(...)
    context: Optional[str] = Field(None, max_length=1000)
    
    @validator('failure_pattern')
    def validate_pattern(cls, v):
        if not v.strip():
            raise ValueError("Failure pattern cannot be empty or whitespace")
        return v.strip()
    
    @validator('context')
    def validate_context(cls, v):
        if v and not v.strip():
            return None
        return v.strip() if v else None


class SuggestionResponseValidator(BaseModel):
    """Validator for suggestion responses."""
    suggestion_id: str
    prediction_confidence: int = Field(..., ge=0, le=100)
    recommended_actions: List[str]
    expected_impact: ImpactLevel
    preventive_measures: List[str]
    created_at: str


class InputValidator:
    """Comprehensive input validation utility."""
    
    # Patterns for validation
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s_\-\.,:;!?()\[\]{}]+$')
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """Validate UUID format."""
        return bool(InputValidator.UUID_PATTERN.match(uuid_str))
    
    @staticmethod
    def validate_confidence_score(score: int) -> bool:
        """Validate confidence score is between 0-100."""
        return isinstance(score, int) and 0 <= score <= 100
    
    @staticmethod
    def validate_is_safe_string(text: str, max_length: int = 1000) -> bool:
        """Validate string is safe and doesn't exceed max length."""
        if len(text) > max_length:
            return False
        return bool(InputValidator.SAFE_STRING_PATTERN.match(text))
    
    @staticmethod
    def sanitize_string(text: str) -> str:
        """Sanitize string input."""
        # Remove leading/trailing whitespace
        text = text.strip()
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        return text
    
    @staticmethod
    def validate_prediction_request(request_data: Dict[str, Any]) -> ValidationResult:
        """Validate prediction request."""
        result = ValidationResult(is_valid=True)
        
        try:
            # Validate using Pydantic model
            PredictionRequestValidator(**request_data)
        except ValidationError as e:
            result.is_valid = False
            result.errors = [str(error) for error in e.errors()]
        
        # Additional validation
        if 'failure_pattern' in request_data:
            pattern = request_data['failure_pattern']
            if not InputValidator.validate_is_safe_string(pattern):
                result.warnings.append("Pattern contains unusual characters")
        
        return result
    
    @staticmethod
    def validate_suggested_actions(actions: List[str]) -> ValidationResult:
        """Validate list of suggested actions."""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(actions, list):
            result.is_valid = False
            result.errors.append("Actions must be a list")
            return result
        
        if len(actions) == 0:
            result.warnings.append("Empty actions list")
        
        for action in actions:
            if len(action) > 500:
                result.warnings.append(f"Action exceeds 500 characters: {action[:50]}...")
        
        return result
    
    @staticmethod
    def validate_impact_level(level: str) -> ValidationResult:
        """Validate impact level."""
        result = ValidationResult(is_valid=True)
        
        try:
            ImpactLevel(level.lower())
        except ValueError:
            result.is_valid = False
            result.errors.append(
                f"Invalid impact level: {level}. Must be one of: high, medium, low"
            )
        
        return result


class ParameterSanitizer:
    """Utility class for sanitizing parameters."""
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary values."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputValidator.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = ParameterSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [ParameterSanitizer.sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized
    
    @staticmethod
    def sanitize_for_database(value: Any) -> Any:
        """Sanitize value for database storage."""
        if isinstance(value, str):
            return InputValidator.sanitize_string(value)
        elif isinstance(value, dict):
            return ParameterSanitizer.sanitize_dict(value)
        return value
