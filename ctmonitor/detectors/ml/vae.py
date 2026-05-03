"""VAE detector wrapper (ONNX-first inference)."""

from __future__ import annotations

from pathlib import Path

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert
from ctmonitor.ml.inference import OnnxPredictor, domain_to_features, sigmoid


class VAEDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "VAEDetector"

    def __init__(self, onnx_path: str = "models/vae.onnx"):
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
            return score, 0.82, {"source": "onnx", "domain": cert.etld_plus1}

        # fallback heuristic reconstruction-error proxy
        pseudo_error = cert.domain_entropy * 1.2
        score = max(0.0, min(1.0, sigmoid((pseudo_error - 0.5) / 0.2)))
        return score, 0.55, {"source": "fallback", "pseudo_error": round(pseudo_error, 4)}
