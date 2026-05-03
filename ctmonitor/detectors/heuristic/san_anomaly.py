"""SAN (Subject Alternative Name) Anomaly Detector."""

import math
from ctmonitor.ingestion.models import NormalisedCert
from ctmonitor.detectors.base import BaseDetector


class SANAnomalyDetector(BaseDetector):
    """
    Detects anomalies in SAN (Subject Alternative Name) certificates.
    
    Indicators:
    - Excessive number of SANs (e.g., >100) suggests cert is reused across many domains
    - Wildcard + specific domains mixed together
    - Domain entropy mismatch (one legitimate brand + many random SANs)
    - SAN domains from different registrars/TLDs
    """
    
    @property
    def name(self) -> str:
        return "SAN Anomaly"
    
    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        """
        Returns (score, confidence, evidence_dict).
        
        Score: 0.0-1.0
        - 0.0: Normal SAN usage
        - 0.5: Suspicious patterns
        - 1.0: Highly anomalous SAN structure
        """
        evidence = {}
        score = 0.0
        confidence = 0.7
        
        # Excessive SAN count (red flag for reused certs)
        san_count = len(cert.san_domains)
        evidence["san_count"] = san_count
        
        if san_count > 100:
            score += 0.5
            evidence["excessive_sans"] = True
        elif san_count > 50:
            score += 0.3
            evidence["high_san_count"] = True
        
        # Wildcard + specific domain mix (unusual)
        has_wildcard = cert.is_wildcard or any("*" in d for d in cert.san_domains)
        has_specific = any("." in d and "*" not in d for d in cert.san_domains)
        
        if has_wildcard and has_specific and san_count > 2:
            score += 0.2
            evidence["wildcard_specific_mix"] = True
        
        # Domain entropy check: If primary domain is low-entropy but SANs are high-entropy
        if cert.domain_entropy > 0.0:
            san_entropies = [self._entropy(d) for d in cert.san_domains[:10]]  # Sample first 10
            avg_san_entropy = sum(san_entropies) / len(san_entropies) if san_entropies else 0.0
            
            if avg_san_entropy > 0.8 and cert.domain_entropy < 0.4:
                score += 0.2
                evidence["entropy_mismatch"] = True
                evidence["primary_entropy"] = round(cert.domain_entropy, 3)
                evidence["avg_san_entropy"] = round(avg_san_entropy, 3)
        
        # TLD diversity check: Many different TLDs suggests cert reuse across unrelated domains
        tlds = set()
        for domain in cert.san_domains[:50]:  # Sample
            if "." in domain:
                tld = domain.split(".")[-1]
                tlds.add(tld)
        
        if len(tlds) > 5:
            score += 0.1
            evidence["high_tld_diversity"] = True
            evidence["unique_tlds"] = len(tlds)
        
        # Clamp score to [0, 1]
        score = min(1.0, max(0.0, score))
        
        evidence["score_factors"] = {
            "excessive_sans": score if san_count > 100 else 0.0,
            "entropy_mismatch": score if avg_san_entropy and avg_san_entropy > 0.8 else 0.0,
            "tld_diversity": score if len(tlds) > 5 else 0.0
        }
        
        return score, confidence, evidence
    
    @staticmethod
    def _entropy(s: str) -> float:
        """Calculate Shannon entropy of a string (0.0 = uniform, 1.0 = highly random)."""
        if not s:
            return 0.0
        
        freq = {}
        for c in s.lower():
            freq[c] = freq.get(c, 0) + 1
        
        ent = 0.0
        for count in freq.values():
            p = count / len(s)
            ent -= p * math.log2(p)
        
        # Normalize to [0, 1]
        max_ent = math.log2(min(26, len(freq)))
        return ent / max_ent if max_ent > 0 else 0.0
