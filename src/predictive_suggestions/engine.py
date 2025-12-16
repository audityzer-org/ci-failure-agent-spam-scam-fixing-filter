"""Core suggestion engine for generating recommendations."""

import logging
from typing import List, Optional, Dict, Any
from .models import Suggestion, SuggestionType, Alert
from .rules import RuleRepository

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Rule-based suggestion engine for alerts."""
    
    def __init__(self):
        self.rule_repo = RuleRepository()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_suggestions(
        self,
        alert_text: str,
        alert_type: str,
        confidence_threshold: float = 0.7
    ) -> List[Suggestion]:
        """Generate suggestions for an alert.
        
        Args:
            alert_text: The alert message/description
            alert_type: Type of alert (CI_FAILURE or SECURITY_INCIDENT)
            confidence_threshold: Minimum confidence score for suggestions
            
        Returns:
            List of suggestions sorted by confidence
        """
        suggestions: List[Suggestion] = []
        rules = self.rule_repo.get_all_rules()
        
        for rule in rules:
            if not rule.enabled:
                continue
                
            # Match rule against alert text
            match = self.rule_repo.match_rule(rule, alert_text)
            
            if match.matched and match.match_score >= confidence_threshold:
                suggestion = self._create_suggestion_from_rule(
                    rule, match, alert_text
                )
                suggestions.append(suggestion)
        
        # Sort by confidence descending
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions
    
    def _create_suggestion_from_rule(
        self,
        rule,
        match,
        alert_text: str
    ) -> Suggestion:
        """Create a suggestion from a matched rule."""
        # Expand templates with context
        title = rule.title_template
        description = rule.description_template
        
        # Add metadata about the match
        metadata: Dict[str, Any] = {
            'rule_id': rule.rule_id,
            'matched_text': match.matched_text,
            'created_at': rule.created_at.isoformat() if rule.created_at else None,
        }
        
        return Suggestion(
            type=rule.suggestion_type,
            confidence=match.match_score,
            title=title,
            description=description,
            actions=rule.actions,
            severity=rule.severity,
            metadata=metadata
        )
    
    def rank_suggestions(
        self,
        suggestions: List[Suggestion]
    ) -> List[Suggestion]:
        """Rank suggestions by multiple factors.
        
        Args:
            suggestions: List of suggestions to rank
            
        Returns:
            Ranked suggestions
        """
        # Severity weight mapping
        severity_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        # Calculate composite score
        def score_suggestion(s: Suggestion) -> float:
            confidence_score = s.confidence
            severity_weight = severity_weights.get(s.severity, 0.5)
            return confidence_score * severity_weight
        
        # Sort by composite score
        ranked = sorted(suggestions, key=score_suggestion, reverse=True)
        return ranked
    
    def filter_suggestions(
        self,
        suggestions: List[Suggestion],
        severity: Optional[str] = None,
        suggestion_type: Optional[SuggestionType] = None,
        min_confidence: float = 0.0
    ) -> List[Suggestion]:
        """Filter suggestions by criteria.
        
        Args:
            suggestions: List to filter
            severity: Filter by severity level
            suggestion_type: Filter by suggestion type
            min_confidence: Minimum confidence threshold
            
        Returns:
            Filtered suggestions
        """
        filtered = suggestions
        
        if severity:
            filtered = [s for s in filtered if s.severity == severity]
        
        if suggestion_type:
            filtered = [s for s in filtered if s.type == suggestion_type]
        
        if min_confidence > 0:
            filtered = [s for s in filtered if s.confidence >= min_confidence]
        
        return filtered
    
    def batch_generate_suggestions(
        self,
        alerts: List[Dict[str, str]],
        confidence_threshold: float = 0.7
    ) -> Dict[str, List[Suggestion]]:
        """Generate suggestions for multiple alerts.
        
        Args:
            alerts: List of alert dicts with 'text' and 'type' keys
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Dict mapping alert ID to suggestions
        """
        results = {}
        
        for alert in alerts:
            alert_id = alert.get('id', str(hash(alert.get('text', ''))))
            suggestions = self.generate_suggestions(
                alert.get('text', ''),
                alert.get('type', 'UNKNOWN'),
                confidence_threshold
            )
            results[alert_id] = suggestions
        
        return results
