"""Levenshtein Heuristic."""

from rapidfuzz import process, fuzz
from pathlib import Path
from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert

class LevenshteinDetector(BaseDetector):
    name = "LevenshteinDetector"

    def __init__(self, brands_path: str = "data/brands_10k.txt"):
        self.brands = []
        p = Path(brands_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self.brands = [line.strip().lower() for line in f if line.strip()]
        else:
            self.brands = ["paypal", "apple", "microsoft", "google", "amazon"]

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        if not self.brands:
            return 0.0, 0.0, {"error": "No brands loaded"}
            
        best_match = process.extractOne(cert.etld_plus1, self.brands, scorer=fuzz.ratio)
        if not best_match:
            return 0.0, 0.8, {}
            
        brand, ratio, _ = best_match
        if ratio < 70:
            return 0.0, 0.8, {"best_match": brand, "ratio": ratio}
            
        score = min(1.0, float(ratio) / 100.0)
        return score, 0.8, {"matched_brand": brand, "ratio": ratio, "domain": cert.etld_plus1}
