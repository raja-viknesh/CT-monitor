"""Quorum Engine."""

from datetime import datetime, timezone
import time

from ctmonitor.ingestion.models import CertVerdict, CertVerdictTier, NormalisedCert
from ctmonitor.quorum.dempster_shafer import DempsterShafer

class QuorumEngine:
    def __init__(self, detectors: list):
        self.detectors = detectors

    @staticmethod
    def _format_reason(detector_result) -> str:
        evidence_bits = []
        if detector_result.score > 0:
            evidence_bits.append(f"score={detector_result.score:.2f}")
        if detector_result.confidence > 0:
            evidence_bits.append(f"confidence={detector_result.confidence:.2f}")
        for key in ("matched_brand", "matched_keyword", "ratio", "is_idn", "unicode_domain", "domain"):
            if key in detector_result.evidence:
                evidence_bits.append(f"{key}={detector_result.evidence[key]}")
        if not evidence_bits and detector_result.evidence:
            evidence_bits.append(", ".join(f"{k}={v}" for k, v in detector_result.evidence.items()))
        if not evidence_bits:
            evidence_bits.append("no notable evidence")
        return f"{detector_result.detector_name}: " + ", ".join(evidence_bits)

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
        
        # Lightweight local calibration: favor the threat belief, but soften with plausibility.
        risk_score = max(0.0, min(1.0, (0.75 * belief_threat) + (0.25 * plausibility_threat)))
        
        # Compute Tier
        if risk_score >= 0.85: tier = CertVerdictTier.BLOCK
        elif risk_score >= 0.60: tier = CertVerdictTier.WARN
        elif risk_score >= 0.35: tier = CertVerdictTier.WATCH
        else: tier = CertVerdictTier.SAFE
        
        latency = (time.perf_counter() - start_t) * 1000.0

        ranked_results = sorted(results, key=lambda item: (item.score * item.confidence), reverse=True)
        top_signals = [
            {
                "detector_name": item.detector_name,
                "score": item.score,
                "confidence": item.confidence,
                "evidence": item.evidence,
                "latency_ms": item.latency_ms,
            }
            for item in ranked_results
        ]
        reasoning = [self._format_reason(item) for item in ranked_results]
        if cert.is_idn:
            reasoning.append(f"Structural signal: IDN domain {cert.unicode_domain}")
        if cert.is_wildcard:
            reasoning.append("Structural signal: wildcard certificate")
        if cert.cert_duration_days and cert.cert_duration_days < 14:
            reasoning.append(f"Structural signal: short certificate lifetime ({cert.cert_duration_days} days)")

        analysis = {
            "summary": {
                "domain": cert.full_domain,
                "etld_plus1": cert.etld_plus1,
                "tier": tier.value,
                "risk_score": risk_score,
                "belief_threat": belief_threat,
                "plausibility_threat": plausibility_threat,
                "uncertainty": combined["theta"],
            },
            "signals": top_signals,
            "reasoning": reasoning,
            "structural_signals": {
                "is_idn": cert.is_idn,
                "is_wildcard": cert.is_wildcard,
                "san_count": cert.san_count,
                "domain_entropy": cert.domain_entropy,
                "cert_duration_days": cert.cert_duration_days,
                "issuer_cn": cert.issuer_cn,
            },
        }
        
        return CertVerdict(
            domain=cert.full_domain,
            risk_score=risk_score,
            tier=tier,
            confidence_lower=max(0.0, risk_score - combined["theta"]),
            confidence_upper=min(1.0, risk_score + combined["theta"]),
            detector_results=results,
            analysis=analysis,
            combined_belief=belief_threat,
            combined_plausibility=plausibility_threat,
            latency_ms=latency,
            ts=datetime.now(timezone.utc)
        )
