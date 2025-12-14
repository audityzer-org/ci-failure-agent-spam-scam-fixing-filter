"""CI Failure Proposer Module: Analyzes CI failures and suggests fixes."""
import re
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class CIFailureType(Enum):
    """Enumeration of common CI failure types."""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    TEST_FAILURE = "test_failure"
    BUILD_TIMEOUT = "build_timeout"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    PERMISSION_DENIED = "permission_denied"
    OUT_OF_MEMORY = "out_of_memory"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"

@dataclass
class CIFailureProposal:
    """Represents a proposed fix for a CI failure."""
    failure_type: CIFailureType
    issue_description: str
    suggested_fixes: List[str]
    priority: int
    confidence_score: float
    root_cause_analysis: Optional[str] = None
    affected_files: List[str] = field(default_factory=list)
    commands_to_run: List[str] = field(default_factory=list)
    documentation_links: List[str] = field(default_factory=list)

class CIFailurePatternMatcher:
    """Pattern-based matcher for common CI failures."""
    
    def __init__(self):
        self.patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize regex patterns for common CI failures."""
        return {
            "syntax_error": {
                "patterns": [
                    r"SyntaxError.*line \d+",
                    r"\^\s+$",
                    r"Invalid syntax",
                ],
                "type": CIFailureType.SYNTAX_ERROR,
                "priority": 5,
            },
            "import_error": {
                "patterns": [
                    r"ModuleNotFoundError",
                    r"ImportError.*No module",
                    r"cannot import name",
                ],
                "type": CIFailureType.IMPORT_ERROR,
                "priority": 4,
            },
            "test_failure": {
                "patterns": [
                    r"FAILED.*test_",
                    r"AssertionError",
                    r"\d+ failed.*\d+ passed",
                ],
                "type": CIFailureType.TEST_FAILURE,
                "priority": 4,
            },
            "build_timeout": {
                "patterns": [
                    r"timeout",
                    r"Timeout",
                    r"exceeded.*time",
                ],
                "type": CIFailureType.BUILD_TIMEOUT,
                "priority": 3,
            },
        }
    
    def match_failure(self, log_content: str) -> CIFailureType:
        """Match log content to a specific CI failure type."""
        for failure_key, config in self.patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, log_content, re.IGNORECASE | re.MULTILINE):
                    return config["type"]
        return CIFailureType.UNKNOWN

class CIFailureProposer:
    """Main service for proposing CI failure fixes."""
    
    def __init__(self):
        self.pattern_matcher = CIFailurePatternMatcher()
        self.fix_strategies = self._init_fix_strategies()
    
    def _init_fix_strategies(self) -> Dict[CIFailureType, Dict[str, Any]]:
        """Initialize fix strategies for each failure type."""
        return {
            CIFailureType.SYNTAX_ERROR: {
                "fixes": [
                    "Run Python linter to identify syntax errors",
                    "Check indentation consistency",
                    "Validate parentheses and quotes balance",
                ],
                "commands": [
                    "python -m py_compile <file>",
                    "flake8 <file>",
                    "pylint <file>",
                ],
                "root_cause": "Invalid Python syntax in code",
            },
            CIFailureType.IMPORT_ERROR: {
                "fixes": [
                    "Install missing dependencies",
                    "Check PYTHONPATH environment variable",
                    "Verify package is installed",
                ],
                "commands": [
                    "pip install -r requirements.txt",
                    "python -c 'import <module>'",
                ],
                "root_cause": "Missing or incorrectly configured module import",
            },
            CIFailureType.TEST_FAILURE: {
                "fixes": [
                    "Run failing test locally",
                    "Check test assertions",
                    "Verify test data and fixtures",
                ],
                "commands": [
                    "pytest -vvs <test_file>",
                    "pytest --pdb <test_file>",
                ],
                "root_cause": "Unit test assertion failed",
            },
            CIFailureType.BUILD_TIMEOUT: {
                "fixes": [
                    "Increase timeout threshold",
                    "Optimize build process",
                    "Split into smaller build jobs",
                ],
                "commands": [],
                "root_cause": "Build/test execution exceeded time limit",
            },
        }
    
    def propose_fixes(self, log_content: str, context: Optional[Dict[str, Any]] = None) -> CIFailureProposal:
        """Analyze CI failure logs and propose fixes."""
        failure_type = self.pattern_matcher.match_failure(log_content)
        strategy = self.fix_strategies.get(failure_type, {})
        
        if context is None:
            context = {}
        
        proposal = CIFailureProposal(
            failure_type=failure_type,
            issue_description=f"Detected {failure_type.value} from CI logs",
            suggested_fixes=strategy.get("fixes", []),
            priority=strategy.get("priority", 1),
            confidence_score=self._calculate_confidence(log_content, failure_type),
            root_cause_analysis=strategy.get("root_cause"),
            commands_to_run=strategy.get("commands", []),
            affected_files=context.get("affected_files", []),
        )
        
        return proposal
    
    def _calculate_confidence(self, log_content: str, failure_type: CIFailureType) -> float:
        """Calculate confidence score for the failure type classification."""
        if failure_type == CIFailureType.UNKNOWN:
            return 0.3
        
        base_confidence = min(0.9, 0.5 + 0.2)
        return base_confidence
