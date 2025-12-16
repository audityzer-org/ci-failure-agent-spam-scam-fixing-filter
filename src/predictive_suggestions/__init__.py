"""Predictive Suggestions Module

Rule-based recommendation service for CI failures and security incidents.
Provides fallback when the main predictive-propositions-service is unavailable.
"""

from .engine import SuggestionEngine
from .models import SuggestionRule, SuggestionType
from .rules import RuleRepository
from .engine import SuggestionEngine

__all__ = ['SuggestionEngine', 'SuggestionRule', 'SuggestionType', 'Suggestion', 'RuleRepository']
