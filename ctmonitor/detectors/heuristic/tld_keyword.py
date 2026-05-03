"""TLD Keyword Detector."""

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert
import yaml
from pathlib import Path

class TLDKeywordDetector(BaseDetector):
    name = "TLDKeywordDetector"

    def __init__(self, rules_path: str = "data/tld_rules.yaml"):
        self.rules = []
        p = Path(rules_path)
        if p.exists():
            with open(p, "r") as f:
                self.rules = yaml.safe_load(f) or []

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        domain = cert.full_domain.lower()
        
        # Simple fallback rule: keyword "login" or "secure" in unusual TLDs
        suspicious_keywords = ["login", "secure", "auth", "account"]
        
        for kw in suspicious_keywords:
            if kw in domain and cert.etld_plus1.endswith((".xyz", ".top", ".pw", ".site")):
                return 0.9, 0.85, {"matched_keyword": kw, "tld": cert.etld_plus1.split(".")[-1]}
                
        return 0.0, 0.85, {}
