"""Tests for predictive suggestions rules."""

import pytest
from src.predictive_suggestions import (
    SuggestionType, RuleRepository
)


class TestRuleRepository:
    """Test RuleRepository functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.repo = RuleRepository()
    
    def test_repository_initialization(self):
        """Test that repository initializes with default rules."""
        rules = self.repo.get_all_rules()
        assert len(rules) == 8  # 4 CI + 4 Security
        assert all(rule.enabled for rule in rules)
    
    def test_get_rule_by_id(self):
        """Test retrieving rule by ID."""
        rule = self.repo.get_rule('test_failure_001')
        assert rule is not None
        assert rule.rule_id == 'test_failure_001'
        assert rule.suggestion_type == SuggestionType.TEST_FAILURE_FIX
    
    def test_ci_failure_rules(self):
        """Test that all CI failure rules are defined."""
        ci_rules = ['test_failure_001', 'build_error_001', 'timeout_001', 'dependency_001']
        for rule_id in ci_rules:
            rule = self.repo.get_rule(rule_id)
            assert rule is not None
            assert rule.enabled
    
    def test_security_rules(self):
        """Test that all security rules are defined."""
        security_rules = [
            'security_phishing_001',
            'security_malware_001',
            'security_social_eng_001',
            'security_scam_001'
        ]
        for rule_id in security_rules:
            rule = self.repo.get_rule(rule_id)
            assert rule is not None
            assert rule.enabled
    
    def test_match_assertion_error(self):
        """Test matching assertion error pattern."""
        rule = self.repo.get_rule('test_failure_001')
        match = self.repo.match_rule(rule, "AssertionError: value mismatch")
        assert match.matched
        assert match.match_score == 0.95
    
    def test_match_syntax_error(self):
        """Test matching syntax error pattern."""
        rule = self.repo.get_rule('build_error_001')
        match = self.repo.match_rule(rule, "SyntaxError in module.py")
        assert match.matched
        assert match.match_score == 0.98
    
    def test_match_phishing(self):
        """Test matching phishing pattern."""
        rule = self.repo.get_rule('security_phishing_001')
        match = self.repo.match_rule(rule, "Verify your account immediately")
        assert match.matched
        assert match.match_score == 0.85
    
    def test_match_scam(self):
        """Test matching scam pattern."""
        rule = self.repo.get_rule('security_scam_001')
        match = self.repo.match_rule(rule, "Wire $1000 to claim prize")
        assert match.matched
        assert match.match_score == 0.93
    
    def test_no_match(self):
        """Test non-matching text."""
        rule = self.repo.get_rule('test_failure_001')
        match = self.repo.match_rule(rule, "Random text with no patterns")
        assert not match.matched
        assert match.match_score == 0.0
    
    def test_rule_metadata(self):
        """Test rule metadata completeness."""
        rule = self.repo.get_rule('test_failure_001')
        assert rule.title_template is not None
        assert rule.description_template is not None
        assert len(rule.actions) > 0
        assert rule.severity in ['low', 'medium', 'high', 'critical']
    
    def test_disabled_rule_no_match(self):
        """Test that disabled rules don't match."""
        rule = self.repo.get_rule('test_failure_001')
        rule.enabled = False
        match = self.repo.match_rule(rule, "AssertionError")
        assert not match.matched
        assert match.match_score == 0.0
