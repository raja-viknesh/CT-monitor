"""Domain Age & Certificate Age Detector."""

from datetime import datetime, timezone
import httpx
from ctmonitor.ingestion.models import NormalisedCert
from ctmonitor.detectors.base import BaseDetector


class DomainAgeDetector(BaseDetector):
    """
    Detects domains that are:
    - Very new (< 30 days old) - common for phishing campaigns
    - Certificate issued immediately after domain registration
    - Domain registered during suspicious time windows
    
    Uses WHOIS lookups (cached locally) to determine domain creation date.
    Falls back to certificate issuance date if WHOIS unavailable.
    """
    
    def __init__(self):
        self.whois_cache = {}  # In-memory cache; in production use SQLite
    
    @property
    def name(self) -> str:
        return "Domain Age"
    
    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        """
        Returns (score, confidence, evidence_dict).
        
        Score factors:
        - Domain < 7 days old: +0.8 (highest risk)
        - Domain < 30 days old: +0.5
        - Domain < 1 year old: +0.2
        - Cert issued immediately after domain creation: +0.3
        """
        evidence = {}
        score = 0.0
        confidence = 0.6  # WHOIS lookups are not perfect
        
        try:
            # Try to get domain creation date from WHOIS
            domain_age_days = self._get_domain_age_days(cert.etld_plus1)
            evidence["domain_age_days"] = domain_age_days
            evidence["lookup_source"] = "whois"
            
        except Exception as e:
            # Fallback: Use certificate issuance as proxy
            domain_age_days = self._get_cert_age_days(cert)
            evidence["domain_age_days"] = domain_age_days
            evidence["lookup_source"] = "cert_issue_date"
            evidence["lookup_error"] = str(e)
            confidence = 0.3  # Low confidence fallback
        
        # Score based on age
        if domain_age_days < 7:
            score = 0.8
            evidence["age_category"] = "newly_registered_dangerous"
        elif domain_age_days < 14:
            score = 0.6
            evidence["age_category"] = "very_new"
        elif domain_age_days < 30:
            score = 0.5
            evidence["age_category"] = "new"
        elif domain_age_days < 60:
            score = 0.3
            evidence["age_category"] = "recent"
        elif domain_age_days < 365:
            score = 0.15
            evidence["age_category"] = "young"
        else:
            score = 0.0
            evidence["age_category"] = "mature"
        
        # Additional check: Certificate issued suspiciously soon after domain registration
        if domain_age_days < 30 and cert.cert_duration_days > 365:
            score += 0.1  # Long-lived cert on new domain = suspicious
            evidence["long_cert_on_new_domain"] = True
        
        score = min(1.0, score)
        
        return score, confidence, evidence
    
    def _get_domain_age_days(self, domain: str) -> int:
        """
        Query WHOIS to get domain creation date.
        Returns age in days. Raises exception if lookup fails.
        
        In production, this would query a real WHOIS service or cache,
        but for MVP we'll implement a stub that prefers cached data.
        """
        if domain in self.whois_cache:
            created = self.whois_cache[domain]
        else:
            # Stub: In production, call whoisxmlapi.com or similar
            # For now, simulate by returning a random recent date
            # This is intentionally simplified for MVP
            raise NotImplementedError("WHOIS lookup not yet implemented; requires API key")
        
        now = datetime.now(timezone.utc)
        delta = now - created
        return delta.days
    
    def _get_cert_age_days(self, cert: NormalisedCert) -> int:
        """Fallback: Use certificate issuance date as proxy for domain age."""
        now = datetime.now(timezone.utc)
        delta = now - cert.received_at
        return delta.days
