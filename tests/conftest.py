"""Pytest configuration and shared fixtures for CT Monitor tests."""

import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator

from ctmonitor.ingestion.models import (
    CertEvent,
    NormalisedCert,
    DetectorResult,
    CertVerdict,
    CertVerdictTier,
)


@pytest.fixture
def sample_cert_event() -> CertEvent:
    """Create a sample CertEvent for testing."""
    return CertEvent(
        domain="example.com",
        san_list=["example.com", "www.example.com", "mail.example.com"],
        issuer_cn="Let's Encrypt Authority X3",
        org="Example Inc.",
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc) + timedelta(days=90),
        log_id="google-xenotaph-2024",
        fingerprint_sha256="abcdef1234567890" * 4,
        raw_json={"source": "certstream", "chain": []},
    )


@pytest.fixture
def malicious_cert_event() -> CertEvent:
    """Create a sample malicious/phishing CertEvent."""
    return CertEvent(
        domain="paypa1-login.com",  # Typosquatting of PayPal
        san_list=["paypa1-login.com", "www.paypa1-login.com"],
        issuer_cn="DV SSL Authority",
        org=None,
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc) + timedelta(days=365),
        log_id="google-xenotaph-2024",
        fingerprint_sha256="deadbeef1234567890" * 4,
        raw_json={"source": "certstream"},
    )


@pytest.fixture
def sample_normalised_cert(sample_cert_event: CertEvent) -> NormalisedCert:
    """Create a sample NormalisedCert."""
    return NormalisedCert(
        etld_plus1="example.com",
        full_domain="www.example.com",
        san_domains=["example.com", "www.example.com", "mail.example.com"],
        issuer_cn="Let's Encrypt Authority X3",
        org="Example Inc.",
        cert_duration_days=90,
        is_wildcard=False,
        is_idn=False,
        unicode_domain="example.com",
        fingerprint=sample_cert_event.fingerprint_sha256,
        received_at=datetime.now(timezone.utc),
        san_count=3,
        domain_entropy=0.75,
        key_bits=2048,
    )


@pytest.fixture
def sample_detector_result() -> DetectorResult:
    """Create a sample DetectorResult."""
    return DetectorResult(
        detector_name="LevenshteinDetector",
        score=0.42,
        confidence=0.80,
        evidence={
            "matched_brand": "example",
            "ratio": 95.5,
            "domain": "example.com",
        },
        latency_ms=1.23,
    )


@pytest.fixture
def sample_cert_verdict(sample_detector_result: DetectorResult) -> CertVerdict:
    """Create a sample CertVerdict."""
    return CertVerdict(
        domain="example.com",
        risk_score=0.42,
        tier=CertVerdictTier.WATCH,
        confidence_lower=0.35,
        confidence_upper=0.52,
        detector_results=[sample_detector_result],
        combined_belief=0.40,
        combined_plausibility=0.55,
        latency_ms=5.67,
        ts=datetime.now(timezone.utc),
    )


@pytest.fixture
def tmp_db_path() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "ctmonitor_test.db"


@pytest.fixture
def tmp_models_dir() -> Path:
    """Create a temporary models directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# Async test helpers
@pytest.fixture
async def async_sample_cert_event() -> CertEvent:
    """Async version of sample_cert_event for async tests."""
    return CertEvent(
        domain="example.com",
        san_list=["example.com", "www.example.com"],
        issuer_cn="Let's Encrypt Authority X3",
        org="Example Inc.",
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc) + timedelta(days=90),
        log_id="google-xenotaph-2024",
        fingerprint_sha256="abcdef1234567890" * 4,
        raw_json={"source": "certstream"},
    )
