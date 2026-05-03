"""Conformal prediction wrapper for detector uncertainty intervals."""

from __future__ import annotations

from typing import Iterable
import numpy as np

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert


class ConformalWrapper:
    def __init__(self, detector: BaseDetector, calibration_scores: Iterable[float] | None = None):
        self.detector = detector
        self.calibration_scores = list(calibration_scores or [0.1, 0.15, 0.2, 0.12, 0.18])

    def predict_with_interval(self, cert: NormalisedCert, alpha: float = 0.05) -> tuple[float, float, float]:
        result = self.detector.analyze(cert)
        score = float(result.score)
        n = max(1, len(self.calibration_scores))
        q_level = min(1.0, (1 - alpha) * (1 + 1 / n))
        q_hat = float(np.quantile(self.calibration_scores, q_level))

        lower = max(0.0, score - q_hat)
        upper = min(1.0, score + q_hat)
        return score, lower, upper
