"""Normaliser for raw certificate events."""

import tldextract
import math
from datetime import datetime, timezone
import encodings.idna

from ctmonitor.ingestion.models import CertEvent, NormalisedCert


class Normaliser:
    """Pipelines raw CertEvents into structured, OCSF-inspired NormalisedCerts."""

    def __init__(self) -> None:
        self.extract = tldextract.TLDExtract(
            cache_dir=False,  # No file caching to prevent storage bloat over time
            suffix_list_urls=None # Use bundled list for local-first operations
        )

    def process(self, event: CertEvent) -> NormalisedCert:
        """Process a CertEvent, extracting TLDs, decoding Punycode, and enriching."""
        
        domain = event.domain.lower()
        extracted = self.extract(domain)
        etld_plus1 = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain

        # Punycode checks
        is_idn = domain.startswith("xn--") or "xn--" in domain
        unicode_domain = domain
        if is_idn:
            try:
                unicode_domain = domain.encode("utf-8").decode("idna")
            except UnicodeError:
                pass  # Fallback to ASCII if decode fails

        # Wildcard checks
        is_wildcard = domain.startswith("*.")

        # Duration
        duration_days = max(
            0, (event.not_after - event.not_before).days
        )

        return NormalisedCert(
            etld_plus1=etld_plus1,
            full_domain=domain,
            san_domains=[s.lower() for s in event.san_list],
            issuer_cn=event.issuer_cn,
            org=event.org,
            cert_duration_days=duration_days,
            is_wildcard=is_wildcard,
            is_idn=is_idn,
            unicode_domain=unicode_domain,
            fingerprint=event.fingerprint_sha256,
            received_at=datetime.now(timezone.utc),
            san_count=len(set(event.san_list)),
            domain_entropy=self._shannon_entropy(domain),
            key_bits=2048 # To be extracted properly from raw_json if keys exist, default 2048
        )

    @staticmethod
    def _shannon_entropy(data: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        occurrences = {}
        for char in data:
            occurrences[char] = occurrences.get(char, 0) + 1
        for count in occurrences.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy
