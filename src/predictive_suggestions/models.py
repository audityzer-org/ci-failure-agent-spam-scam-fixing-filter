"""Data models for predictive suggestions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class SuggestionType(str, Enum):
    """Types of suggestions."""
    # CI failure suggestions
    TEST_FAILURE_FIX = "test_failure_fix"
    BUILD_ERROR_FIX = "build_error_fix"
    TIMEOUT_RESOLUTION = "timeout_resolution"
    DEPENDENCY_UPDATE = "dependency_update"
    
    # Security incident suggestions
    PHISHING_ALERT = "phishing_alert"
    MALWARE_DETECTION = "malware_detection"
    SOCIAL_ENGINEERING = "social_engineering"
    SCAM_DETECTION = "scam_detection"


@dataclass
class Suggestion:
    """A suggestion for handling an alert."""
    type: SuggestionType
    confidence: float  # 0.0 to 1.0
    title: str
    description: str
    actions: List[str]
    severity: str  # "low", "medium", "high", "critical"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuggestionRule:
    """A rule for generating suggestions."""
    rule_id: str
    name: str
    condition_pattern: str  # regex or keyword pattern
    suggestion_type: SuggestionType
    confidence: float
    title_template: str
    description_template: str
    actions: List[str]
    severity: str
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RuleMatch:
    """Result of matching a rule against alert content."""
    rule_id: str
    matched: bool
    match_score: float
    matched_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
