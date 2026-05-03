"""Transformer detector wrapper (ONNX-first inference)."""

from __future__ import annotations

from pathlib import Path

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert
from ctmonitor.ml.inference import OnnxPredictor, domain_to_features, sigmoid


class TransformerDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "TransformerDetector"

    def __init__(self, onnx_path: str = "models/transformer.onnx"):
        self.onnx_path = Path(onnx_path)
        self.predictor = None
        if self.onnx_path.exists():
            try:
                self.predictor = OnnxPredictor(str(self.onnx_path))
            except Exception:
                self.predictor = None

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        features = domain_to_features(cert.etld_plus1)
        if self.predictor:
            score, _ = self.predictor.predict(features)
            return score, 0.90, {"source": "onnx", "domain": cert.etld_plus1}

        risky_tokens = ["login", "secure", "verify", "update", "account", "signin"]
        token_hits = sum(1 for t in risky_tokens if t in cert.full_domain.lower())
        score = max(0.0, min(1.0, sigmoid((token_hits - 1.0) / 1.25)))
        return score, 0.60, {"source": "fallback", "token_hits": token_hits}
