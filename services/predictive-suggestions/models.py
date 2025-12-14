"""Pydantic models for Predictive Propositions Service"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class PropositionItem(BaseModel):
    """Single proposition/recommendation item"""
    id: str = Field(..., description="Unique proposition ID")
    title: str = Field(..., description="Human-readable title")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    category: str = Field(..., description="Category (ci_fix, spam_triage, etc)")
    suggested_action: str = Field(..., description="Recommended action")
    reason: Optional[str] = Field(None, description="Why this proposition")


class SuggestionRequest(BaseModel):
    """Request for getting suggestions"""
    incident_id: str
    incident_type: Literal["ci_failure", "spam_scam", "compliance_violation"]
    failure_type: Optional[str] = None  # For CI: build, test, deploy
    severity: Optional[str] = None  # For Spam: low, medium, high
    error_logs: Optional[List[str]] = None
    context_data: Dict[str, Any] = Field(default_factory=dict)
    user_id: str
    limit: int = Field(default=5, ge=1, le=10)


class SuggestionResponse(BaseModel):
    """Response with suggested propositions"""
    incident_id: str
    propositions: List[PropositionItem]
    served_by: str  # "rule_based_ranker" or "ml_ranker"
    latency_ms: float
    timestamp: str


class FeedbackEvent(BaseModel):
    """User feedback event for tracking"""
    incident_id: str
    proposition_id: str
    user_action: Literal["accepted", "rejected", "skipped"]
    actual_resolution: Optional[str] = None
    timestamp: str
    user_id: str
