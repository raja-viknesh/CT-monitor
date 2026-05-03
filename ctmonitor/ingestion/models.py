"""Data models for CT Monitor — strict OCSF-inspired schema with full type hints."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class CertVerdictTier(Enum):
    """Risk tiers for certificate verdicts."""
    SAFE = "SAFE"
    WATCH = "WATCH"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class CertEvent:
    """
    Raw certificate event from Certstream or RFC 6962 CT log.
    Represents a single certificate issuance event captured from the live stream.
    """
    domain: str
    """Primary domain (Subject CN or first SAN)."""
    
    san_list: list[str]
    """Subject Alternative Names (full list including domain)."""
    
    issuer_cn: str
    """Issuer Common Name (CA identifier)."""
    
    org: Optional[str]
    """Organization field from cert."""
    
    not_before: datetime
    """Certificate validity start (UTC)."""
    
    not_after: datetime
    """Certificate validity end (UTC)."""
    
    log_id: str
    """CT log ID/source identifier."""
    
    fingerprint_sha256: str
    """SHA-256 fingerprint of cert (hex string)."""
    
    raw_json: dict = field(default_factory=dict)
    """Original JSON from Certstream or CT log for audit trail."""

    def __post_init__(self) -> None:
        """Validate that timestamps are UTC aware."""
        if self.not_before.tzinfo is None:
            raise ValueError("not_before must be UTC-aware datetime")
        if self.not_after.tzinfo is None:
            raise ValueError("not_after must be UTC-aware datetime")


@dataclass(frozen=True)
class NormalisedCert:
    """
    Normalised certificate prepared for detector ingestion.
    Applies tldextract, Punycode decoding, deduplication, and enrichment.
    OCSF-inspired schema for structured security events.
    """
    etld_plus1: str
    """Effective TLD + 1 (e.g., "paypal.com")."""
    
    full_domain: str
    """Full domain from certificate (e.g., "secure.paypal-login.com")."""
    
    san_domains: list[str]
    """Decoded Subject Alternative Name domains."""
    
    issuer_cn: str
    """Issuer Common Name."""
    
    org: Optional[str]
    """Organization field."""
    
    cert_duration_days: int
    """Certificate validity duration in days."""
    
    is_wildcard: bool
    """True if domain contains wildcard (e.g., "*.example.com")."""
    
    is_idn: bool
    """True if domain is Internationalized Domain Name (Punycode-encoded)."""
    
    unicode_domain: str
    """Decoded Punycode domain (human-readable Unicode form)."""
    
    fingerprint: str
    """SHA-256 fingerprint (hex string)."""
    
    received_at: datetime
    """Timestamp when certificate was received (UTC)."""
    
    san_count: int = field(default=0)
    """Count of unique SANs (computed from san_domains)."""
    
    domain_entropy: float = field(default=0.0)
    """Shannon entropy of domain name (0.0-1.0)."""
    
    key_bits: int = field(default=0)
    """RSA key size in bits (e.g., 2048, 4096)."""

    def __post_init__(self) -> None:
        """Compute derived fields and validate."""
        # Compute SAN count
        object.__setattr__(self, "san_count", len(set(self.san_domains)))
        
        # Validate timestamp is UTC
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be UTC-aware datetime")


@dataclass(frozen=True)
class DetectorResult:
    """
    Output from a single detector (heuristic or ML).
    Strict contract: a detector must never raise; it returns score=0 with error evidence on exception.
    """
    detector_name: str
    """Detector identifier (e.g., "LevenshteinDetector", "TransformerDetector")."""
    
    score: float
    """Threat score [0.0, 1.0], where 1.0 = high threat."""
    
    confidence: float
    """Detector confidence [0.0, 1.0]. Lower = more uncertainty."""
    
    evidence: dict
    """Structured evidence dictionary for audit trail.
    May contain: matched_brand, ratio, domain, error, latency_ms, etc."""
    
    latency_ms: float
    """End-to-end detector latency in milliseconds."""

    def __post_init__(self) -> None:
        """Validate score and confidence ranges."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.latency_ms < 0:
            raise ValueError(f"latency_ms cannot be negative: {self.latency_ms}")


@dataclass(frozen=True)
class CertVerdict:
    """
    Final verdict on a certificate after detector quorum + calibration.
    This is the primary output of the CTMonitor engine — what is exported to API, SARIF, and storage.
    """
    domain: str
    """Domain under analysis."""
    
    risk_score: float
    """Calibrated threat probability [0.0, 1.0].
    After isotonic calibration, this means: "X% of domains with this profile are malicious"."""
    
    tier: CertVerdictTier
    """Risk classification: BLOCK (≥0.85), WARN (≥0.60), WATCH (≥0.35), SAFE (<0.35)."""
    
    confidence_lower: float
    """Conformal prediction lower bound [0.0, 1.0]."""
    
    confidence_upper: float
    """Conformal prediction upper bound [0.0, 1.0]."""
    
    detector_results: list[DetectorResult]
    """Per-detector breakdown of evidence."""

    analysis: dict
    """Structured explanation payload for UI, export, and audit views."""
    
    combined_belief: float
    """Dempster-Shafer belief_threat component."""
    
    combined_plausibility: float
    """Dempster-Shafer plausibility component."""
    
    latency_ms: float
    """End-to-end inference latency in milliseconds."""
    
    ts: datetime
    """Verdict timestamp (UTC)."""

    def __post_init__(self) -> None:
        """Validate ranges and tier consistency."""
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError(f"risk_score must be in [0.0, 1.0], got {self.risk_score}")
        if not 0.0 <= self.confidence_lower <= 1.0:
            raise ValueError(f"confidence_lower out of range: {self.confidence_lower}")
        if not 0.0 <= self.confidence_upper <= 1.0:
            raise ValueError(f"confidence_upper out of range: {self.confidence_upper}")
        if self.confidence_lower > self.confidence_upper:
            raise ValueError(f"confidence_lower ({self.confidence_lower}) > confidence_upper ({self.confidence_upper})")
        if not 0.0 <= self.combined_belief <= 1.0:
            raise ValueError(f"combined_belief out of range: {self.combined_belief}")
        if not 0.0 <= self.combined_plausibility <= 1.0:
            raise ValueError(f"combined_plausibility out of range: {self.combined_plausibility}")
        if self.ts.tzinfo is None:
            raise ValueError("ts must be UTC-aware datetime")
        
        # Validate tier consistency with risk_score
        expected_tier = self._compute_tier(self.risk_score)
        if self.tier != expected_tier:
            raise ValueError(
                f"tier mismatch: got {self.tier.value} but score {self.risk_score} maps to {expected_tier.value}"
            )

    @staticmethod
    def _compute_tier(risk_score: float) -> CertVerdictTier:
        """Map risk score to tier."""
        if risk_score >= 0.85:
            return CertVerdictTier.BLOCK
        elif risk_score >= 0.60:
            return CertVerdictTier.WARN
        elif risk_score >= 0.35:
            return CertVerdictTier.WATCH
        else:
            return CertVerdictTier.SAFE
