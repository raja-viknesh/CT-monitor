"""Character N-gram language model detector."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from ctmonitor.detectors.base import BaseDetector
from ctmonitor.ingestion.models import NormalisedCert


class CharNgramModel:
    def __init__(self, n: int = 4, k: float = 0.01):
        self.n = n
        self.k = k
        self.counts = Counter()
        self.context_counts = Counter()
        self.vocab = set()
        self.threshold = 20.0
        self.scale = 5.0

    def train(self, domains: list[str]) -> None:
        for domain in domains:
            seq = f"^{domain.lower()}$"
            self.vocab.update(seq)
            for i in range(self.n - 1, len(seq)):
                ngram = seq[i - self.n + 1 : i + 1]
                context = ngram[:-1]
                self.counts[ngram] += 1
                self.context_counts[context] += 1

    def perplexity(self, domain: str) -> float:
        seq = f"^{domain.lower()}$"
        if len(seq) < self.n:
            return 999.0

        vocab_size = max(1, len(self.vocab))
        log_prob = 0.0
        steps = 0
        for i in range(self.n - 1, len(seq)):
            ngram = seq[i - self.n + 1 : i + 1]
            context = ngram[:-1]
            numerator = self.counts[ngram] + self.k
            denominator = self.context_counts[context] + (self.k * vocab_size)
            prob = numerator / denominator
            log_prob += math.log(prob)
            steps += 1

        if steps == 0:
            return 999.0
        return math.exp(-(1.0 / steps) * log_prob)

    def score(self, domain: str) -> float:
        perp = self.perplexity(domain)
        z = (perp - self.threshold) / max(1e-6, self.scale)
        return 1.0 / (1.0 + math.exp(-z))


class NgramLMDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "NgramLMDetector"

    def __init__(self, model: CharNgramModel | None = None):
        self.model = model or CharNgramModel(n=4, k=0.01)

    def _analyze(self, cert: NormalisedCert) -> tuple[float, float, dict]:
        score = float(self.model.score(cert.etld_plus1))
        return score, 0.75, {
            "domain": cert.etld_plus1,
            "perplexity": round(float(self.model.perplexity(cert.etld_plus1)), 4),
            "model": "char-4gram",
        }
