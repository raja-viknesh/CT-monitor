"""ONNX-first inference utilities for CTMonitor ML detectors."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np


class OnnxPredictor:
    """Load and run ONNX models with CPU provider only."""

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.session = None
        self.input_name = None
        self.output_name = None
        self._load_session()

    def _load_session(self) -> None:
        try:
            import onnxruntime as ort
        except Exception as exc:
            raise RuntimeError("onnxruntime is required for OnnxPredictor") from exc

        if not self.model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {self.model_path}")

        self.session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # warmup
        dummy = np.zeros((1, 64), dtype=np.float32)
        for _ in range(10):
            self.session.run([self.output_name], {self.input_name: dummy})

    def predict(self, features: np.ndarray) -> tuple[float, float]:
        if self.session is None:
            raise RuntimeError("ONNX session not initialized")

        start = time.perf_counter()
        output = self.session.run([self.output_name], {self.input_name: features})[0]
        latency_ms = (time.perf_counter() - start) * 1000.0

        score = float(np.squeeze(output))
        score = max(0.0, min(1.0, score))
        return score, latency_ms


def domain_to_features(domain: str, max_len: int = 64) -> np.ndarray:
    """Convert domain string into a fixed numeric feature vector for ONNX models."""
    vec = np.zeros((1, max_len), dtype=np.float32)
    chars = domain.lower()[:max_len]
    for i, ch in enumerate(chars):
        vec[0, i] = (ord(ch) % 128) / 127.0
    return vec


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
