"""Base Detector."""

from abc import ABC, abstractmethod
import time
import logging

from ctmonitor.ingestion.models import NormalisedCert, DetectorResult

logger = logging.getLogger(__name__)

class BaseDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        """Returns (score, confidence, evidence_dict)"""
        pass

    def analyze(self, cert: NormalisedCert) -> DetectorResult:
        start_t = time.perf_counter()
        try:
            score, conf, ev = self._analyze(cert)
        except Exception as e:
            logger.error(f"Detector {self.name} failed: {e}")
            score, conf, ev = 0.0, 0.0, {"error": str(e)}
            
        latency = (time.perf_counter() - start_t) * 1000.0
        return DetectorResult(
            detector_name=self.name,
            score=score,
            confidence=conf,
            evidence=ev,
            latency_ms=latency
        )
