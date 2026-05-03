"""Quorum Engine."""

from ctmonitor.ingestion.models import NormalisedCert, CertVerdict, CertVerdictTier
from ctmonitor.quorum.dempster_shafer import DempsterShafer
from datetime import datetime, timezone
import time

class QuorumEngine:
    def __init__(self, detectors: list):
        self.detectors = detectors

    def evaluate(self, cert: NormalisedCert) -> CertVerdict:
        start_t = time.perf_counter()
        results = [d.analyze(cert) for d in self.detectors]
        
        # Combine evidence
        if not results:
            combined = {"threat": 0.0, "safe": 1.0, "theta": 0.0}
        else:
            combined = DempsterShafer.mass_function(results[0].score, results[0].confidence)
            for res in results[1:]:
                m = DempsterShafer.mass_function(res.score, res.confidence)
                combined = DempsterShafer.combine(combined, m)
                
        belief_threat = combined["threat"]
        plausibility_threat = combined["threat"] + combined["theta"]
        
        # Isotonic calibration placeholder (would use calibration.py in full train setup)
        risk_score = belief_threat
        
        # Compute Tier
        if risk_score >= 0.85: tier = CertVerdictTier.BLOCK
        elif risk_score >= 0.60: tier = CertVerdictTier.WARN
        elif risk_score >= 0.35: tier = CertVerdictTier.WATCH
        else: tier = CertVerdictTier.SAFE
        
        latency = (time.perf_counter() - start_t) * 1000.0
        
        return CertVerdict(
            domain=cert.full_domain,
            risk_score=risk_score,
            tier=tier,
            confidence_lower=max(0.0, risk_score - combined["theta"]),
            confidence_upper=min(1.0, risk_score + combined["theta"]),
            detector_results=results,
            combined_belief=belief_threat,
            combined_plausibility=plausibility_threat,
            latency_ms=latency,
            ts=datetime.now(timezone.utc)
        )
