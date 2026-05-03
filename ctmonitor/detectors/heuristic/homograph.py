"""Homograph Detector."""

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert

class HomographDetector(BaseDetector):
    name = "HomographDetector"

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        if not cert.is_idn:
            return 0.0, 0.95, {"is_idn": False}
        
        # In a full implementation, this integrates TR39 confusable lookups.
        # Here we flag any IDN domain as suspicious for homograph analysis.
        evidence = {
            "is_idn": True,
            "unicode_domain": cert.unicode_domain,
            "ascii_domain": cert.full_domain
        }
        
        return 1.0, 0.95, evidence
