"""Graph-style neighborhood detector (lightweight fallback)."""

from __future__ import annotations

from collections import defaultdict, deque

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert


class GNNDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "GNNDetector"

    def __init__(self, window_size: int = 10000):
        self.window_size = window_size
        self.nodes = deque(maxlen=window_size)
        self.org_index = defaultdict(int)
        self.issuer_index = defaultdict(int)

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        org_hits = self.org_index[cert.org or "unknown"]
        issuer_hits = self.issuer_index[cert.issuer_cn]

        score = 0.0
        if cert.domain_entropy > 0.75:
            score += 0.35
        if cert.san_count > 15:
            score += 0.25
        if cert.is_wildcard:
            score += 0.15
        if org_hits > 100:
            score += 0.15
        if issuer_hits > 200:
            score += 0.10
        score = max(0.0, min(1.0, score))

        self.nodes.append(cert.fingerprint)
        self.org_index[cert.org or "unknown"] += 1
        self.issuer_index[cert.issuer_cn] += 1

        return score, 0.78, {
            "window_nodes": len(self.nodes),
            "org_hits": org_hits,
            "issuer_hits": issuer_hits,
            "entropy": round(cert.domain_entropy, 4),
            "san_count": cert.san_count,
        }
