"""SARIF 2.1.0 Export."""

import json
from ctmonitor.ingestion.models import CertVerdict

class SarifReporter:
    @staticmethod
    def generate(verdicts: list[CertVerdict]) -> dict:
        results = []
        for v in verdicts:
            severity = "note"
            if v.tier.value == "BLOCK": severity = "error"
            elif v.tier.value == "WARN": severity = "warning"
            elif v.tier.value == "SAFE": continue
            
            results.append({
                "ruleId": v.tier.value,
                "message": {"text": f"{v.domain} — risk {v.risk_score:.2f}"},
                "level": severity,
                "partialFingerprints": {"attackTechnique": "T1588.004"},
                "properties": {
                    "latency_ms": v.latency_ms,
                    "confidence_lower": v.confidence_lower,
                    "confidence_upper": v.confidence_upper
                }
            })
            
        return {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "CTMonitor",
                        "version": "0.1.0"
                    }
                },
                "results": results
            }]
        }
