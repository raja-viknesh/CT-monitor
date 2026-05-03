"""Hawkes-process style burst detector."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert


class HawkesDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "HawkesDetector"

    def __init__(self, mu: float = 1.0, alpha: float = 0.5, beta: float = 0.8):
        self.mu = mu
        self.alpha = alpha
        self.beta = beta
        self.history = defaultdict(list)

    def _key(self, cert: NormalisedCert) -> str:
        return f"{cert.org or 'unknown'}::{cert.issuer_cn}"

    def _intensity(self, now_ts: float, events: list[float]) -> float:
        total = self.mu
        for t_i in events:
            if t_i < now_ts:
                total += self.alpha * math.exp(-self.beta * (now_ts - t_i))
        return total

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        key = self._key(cert)
        now_ts = cert.received_at.timestamp()
        events = self.history[key]

        lam = self._intensity(now_ts, events)
        burst_score = 0.0 if self.mu <= 0 else (lam - self.mu) / self.mu
        burst_score = max(0.0, min(1.0, burst_score))

        events.append(now_ts)
        if len(events) > 10000:
            del events[:-10000]

        return burst_score, 0.70, {
            "key": key,
            "events": len(events),
            "lambda": round(lam, 6),
            "mu": self.mu,
        }
