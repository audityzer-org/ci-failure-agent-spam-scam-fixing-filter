"""Predictive Suggestions Package: AI-powered proposal system for CI failures and security incidents."""

from .ci_failure_proposer import (
    CIFailureType,
    CIFailureProposal,
    CIFailurePatternMatcher,
    CIFailureProposer,
)

from .spam_scam_proposer import (
    SpamScamType,
    TriageAction,
    SpamScamProposal,
    SpamScamPatternMatcher,
    SpamScamProposer,
)

from .logging_pipeline import (
    ProposalSource,
    ProposalLogEntry,
    ProposalLogger,
    PostgreSQLStorageBackend,
    MLRankingFeeder,
)

__version__ = "0.1.0"
__author__ = "Audityzer DevOps Team"

__all__ = [
    "CIFailureType",
    "CIFailureProposal",
    "CIFailurePatternMatcher",
    "CIFailureProposer",
    "SpamScamType",
    "TriageAction",
    "SpamScamProposal",
    "SpamScamPatternMatcher",
    "SpamScamProposer",
    "ProposalSource",
    "ProposalLogEntry",
    "ProposalLogger",
    "PostgreSQLStorageBackend",
    "MLRankingFeeder",
]
