"""Spam/Scam Detection & Triage Proposer Module."""
import re
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class SpamScamType(Enum):
    """Classification of spam/scam incident types."""
    PHISHING = "phishing"
    MALWARE = "malware"
    CREDENTIAL_THEFT = "credential_theft"
    DOS_ATTACK = "dos_attack"
    INJECTION_ATTACK = "injection_attack"
    SOCIAL_ENGINEERING = "social_engineering"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FALSE_POSITIVE = "false_positive"
    UNKNOWN = "unknown"

class TriageAction(Enum):
    """Recommended actions for spam/scam incidents."""
    IGNORE = "ignore"
    ISOLATE = "isolate"
    REPORT = "report"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"
    BLOCK = "block"
    MONITOR = "monitor"
    QUARANTINE = "quarantine"

@dataclass
class SpamScamProposal:
    """Represents a proposed action for spam/scam incident."""
    incident_type: SpamScamType
    detected_patterns: List[str]
    recommended_action: TriageAction
    risk_score: float
    confidence_score: float
    description: str
    affected_resources: List[str] = field(default_factory=list)
    escalation_contacts: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation_steps: List[str] = field(default_factory=list)

class SpamScamPatternMatcher:
    """Pattern-based detection for spam/scam incidents."""
    
    def __init__(self):
        self.patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[SpamScamType, List[str]]:
        """Initialize detection patterns for spam/scam types."""
        return {
            SpamScamType.PHISHING: [
                r"click.*here.*verify|urgent.*action.*required",
                r"confirm.*identity|update.*payment.*details",
                r"suspicious.*activity.*detected",
            ],
            SpamScamType.MALWARE: [
                r"trojan|virus|ransomware|backdoor",
                r"malicious.*executable|unsigned.*driver",
            ],
            SpamScamType.CREDENTIAL_THEFT: [
                r"password.*reset|username.*change|login.*attempt",
                r"brute.*force|credential.*stuffing",
            ],
            SpamScamType.DOS_ATTACK: [
                r"ddos|denial.*service|request.*timeout",
                r"connection.*flood|bandwidth.*saturation",
            ],
            SpamScamType.INJECTION_ATTACK: [
                r"sql.*injection|xss|command.*injection",
                r"script.*injection|payload.*detected",
            ],
            SpamScamType.SOCIAL_ENGINEERING: [
                r"pretexting|manipulation|deception",
                r"trust.*exploitation|authority.*misrepresentation",
            ],
        }
    
    def detect_type(self, content: str) -> SpamScamType:
        """Detect spam/scam type from content."""
        for incident_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return incident_type
        return SpamScamType.UNKNOWN

class SpamScamProposer:
    """Main service for proposing spam/scam incident responses."""
    
    def __init__(self):
        self.pattern_matcher = SpamScamPatternMatcher()
        self.action_strategies = self._init_action_strategies()
    
    def _init_action_strategies(self) -> Dict[SpamScamType, Dict[str, Any]]:
        """Initialize action strategies for each incident type."""
        return {
            SpamScamType.PHISHING: {
                "action": TriageAction.ISOLATE,
                "risk_score": 0.8,
                "remediation": [
                    "Block sender domain",
                    "Reset user credentials",
                    "Audit account activity",
                    "Notify affected users",
                ],
                "contacts": ["security@org.com", "incident.response@org.com"],
            },
            SpamScamType.MALWARE: {
                "action": TriageAction.ESCALATE,
                "risk_score": 0.95,
                "remediation": [
                    "Isolate infected system",
                    "Run malware scan",
                    "Restore from clean backup",
                    "Update antivirus signatures",
                ],
                "contacts": ["ciso@org.com", "incident.response@org.com"],
            },
            SpamScamType.CREDENTIAL_THEFT: {
                "action": TriageAction.INVESTIGATE,
                "risk_score": 0.85,
                "remediation": [
                    "Force password reset",
                    "Enable MFA",
                    "Review access logs",
                    "Check for data exfiltration",
                ],
                "contacts": ["security@org.com"],
            },
            SpamScamType.DOS_ATTACK: {
                "action": TriageAction.BLOCK,
                "risk_score": 0.7,
                "remediation": [
                    "Activate DDoS protection",
                    "Rate limit requests",
                    "Redirect traffic",
                    "Monitor service health",
                ],
                "contacts": ["infrastructure@org.com"],
            },
        }
    
    def propose_action(self, incident_content: str, context: Optional[Dict[str, Any]] = None) -> SpamScamProposal:
        """Analyze incident and propose appropriate action."""
        incident_type = self.pattern_matcher.detect_type(incident_content)
        strategy = self.action_strategies.get(incident_type, {})
        
        if context is None:
            context = {}
        
        proposal = SpamScamProposal(
            incident_type=incident_type,
            detected_patterns=[],
            recommended_action=strategy.get("action", TriageAction.INVESTIGATE),
            risk_score=strategy.get("risk_score", 0.5),
            confidence_score=0.75,
            description=f"Detected {incident_type.value} incident",
            affected_resources=context.get("affected_resources", []),
            escalation_contacts=strategy.get("contacts", []),
            remediation_steps=strategy.get("remediation", []),
        )
        
        return proposal
