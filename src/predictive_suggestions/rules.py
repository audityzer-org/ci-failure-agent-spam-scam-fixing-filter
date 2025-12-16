"""Suggestion rules for CI failures and security incidents."""

import re
from typing import List, Dict
from .models import SuggestionRule, SuggestionType, RuleMatch
from datetime import datetime


class RuleRepository:
    """Repository of built-in rules for suggestions."""
    
    def __init__(self):
        self.rules: Dict[str, SuggestionRule] = {}
        self._init_ci_failure_rules()
        self._init_security_rules()
    
    def _init_ci_failure_rules(self) -> None:
        """Initialize CI failure rules."""
        # Test failures
        self.rules['test_failure_001'] = SuggestionRule(
            rule_id='test_failure_001',
            name='Assertion Error Detection',
            condition_pattern=r'AssertionError|assert.*failed|Test.*failed',
            suggestion_type=SuggestionType.TEST_FAILURE_FIX,
            confidence=0.95,
            title_template='Fix Assertion Error in Test Suite',
            description_template='The test suite encountered an assertion error. Review the test expectations and verify the actual output matches expected values.',
            actions=['Review test expectations', 'Check assertion values', 'Fix test logic', 'Run tests locally'],
            severity='high'
        )
        
        # Build errors
        self.rules['build_error_001'] = SuggestionRule(
            rule_id='build_error_001',
            name='Compilation Error Detection',
            condition_pattern=r'compilation failed|SyntaxError|ImportError|ModuleNotFoundError',
            suggestion_type=SuggestionType.BUILD_ERROR_FIX,
            confidence=0.98,
            title_template='Fix Build Compilation Error',
            description_template='The build failed due to a compilation error. Check the error message for syntax issues or missing imports.',
            actions=['Check syntax', 'Verify imports', 'Fix error', 'Rebuild'],
            severity='critical'
        )
        
        # Timeout
        self.rules['timeout_001'] = SuggestionRule(
            rule_id='timeout_001',
            name='Test Timeout Detection',
            condition_pattern=r'timeout|exceeded.*time|operation.*timed out',
            suggestion_type=SuggestionType.TIMEOUT_RESOLUTION,
            confidence=0.92,
            title_template='Resolve Test Timeout',
            description_template='A test or operation exceeded the time limit. Consider optimizing the code or increasing the timeout.',
            actions=['Profile performance', 'Optimize code', 'Increase timeout', 'Check for infinite loops'],
            severity='medium'
        )
        
        # Dependency errors
        self.rules['dependency_001'] = SuggestionRule(
            rule_id='dependency_001',
            name='Dependency Version Conflict',
            condition_pattern=r'version conflict|dependency.*mismatch|incompatible.*version',
            suggestion_type=SuggestionType.DEPENDENCY_UPDATE,
            confidence=0.88,
            title_template='Resolve Dependency Version Conflict',
            description_template='There is a dependency version conflict. Update the version constraints in your configuration files.',
            actions=['Check requirements', 'Update versions', 'Run dependency check', 'Test integration'],
            severity='medium'
        )
    
    def _init_security_rules(self) -> None:
        """Initialize security incident rules."""
        # Phishing
        self.rules['security_phishing_001'] = SuggestionRule(
            rule_id='security_phishing_001',
            name='Phishing Detection',
            condition_pattern=r'phishing|suspicious.*email|verify.*account|confirm.*password',
            suggestion_type=SuggestionType.PHISHING_ALERT,
            confidence=0.85,
            title_template='Potential Phishing Alert',
            description_template='This may be a phishing attempt. Never click suspicious links or provide credentials.',
            actions=['Report to security team', 'Do not click links', 'Do not provide credentials', 'Delete message'],
            severity='critical'
        )
        
        # Malware
        self.rules['security_malware_001'] = SuggestionRule(
            rule_id='security_malware_001',
            name='Malware Detection',
            condition_pattern=r'malware|suspicious.*file|virus.*detected|quarantine',
            suggestion_type=SuggestionType.MALWARE_DETECTION,
            confidence=0.96,
            title_template='Malware Detected',
            description_template='A potential malware has been detected. Quarantine the file and scan the system.',
            actions=['Isolate file', 'Run antivirus scan', 'Report incident', 'Review logs'],
            severity='critical'
        )
        
        # Social engineering
        self.rules['security_social_eng_001'] = SuggestionRule(
            rule_id='security_social_eng_001',
            name='Social Engineering Detection',
            condition_pattern=r'urgent action|verify identity|confirm details|claim.*reward',
            suggestion_type=SuggestionType.SOCIAL_ENGINEERING,
            confidence=0.8,
            title_template='Potential Social Engineering Attempt',
            description_template='This appears to be a social engineering attempt. Be cautious and verify through official channels.',
            actions=['Verify independently', 'Contact official support', 'Report incident', 'Educate team'],
            severity='high'
        )
        
        # Scam
        self.rules['security_scam_001'] = SuggestionRule(
            rule_id='security_scam_001',
            name='Scam Detection',
            condition_pattern=r'financial.*offer|lottery.*winner|prize|wire.*transfer|urgent.*payment',
            suggestion_type=SuggestionType.SCAM_DETECTION,
            confidence=0.93,
            title_template='Potential Scam Alert',
            description_template='This is likely a scam attempt. Do not send money or personal information.',
            actions=['Report to authorities', 'Block sender', 'Delete message', 'Notify team'],
            severity='high'
        )
    
    def get_rule(self, rule_id: str) -> SuggestionRule:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
    
    def get_all_rules(self) -> List[SuggestionRule]:
        """Get all rules."""
        return list(self.rules.values())
    
    def match_rule(self, rule: SuggestionRule, text: str) -> RuleMatch:
        """Match a rule against text."""
        if not rule.enabled:
            return RuleMatch(
                rule_id=rule.rule_id,
                matched=False,
                match_score=0.0
            )
        
        try:
            matches = re.findall(rule.condition_pattern, text, re.IGNORECASE)
            if matches:
                return RuleMatch(
                    rule_id=rule.rule_id,
                    matched=True,
                    match_score=rule.confidence,
                    matched_text=matches[0] if matches else None
                )
        except re.error:
            pass
        
        return RuleMatch(
            rule_id=rule.rule_id,
            matched=False,
            match_score=0.0
        )
