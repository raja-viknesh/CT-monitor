"""RFC 6962 CT Log Poller — fetch certificates from official CT logs."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ctmonitor.ingestion.models import CertEvent


logger = logging.getLogger(__name__)


class CTLogPoller:
    """
    Polls public CT logs (RFC 6962) for certificates.
    Can backfill historical data or augment real-time ingestion.
    
    Supports multiple log servers:
    - Google Argon2024, Xenon2024
    - DigiCert CT logs
    - Let's Encrypt Clang Halo
    - Sectigo Mammoth
    """
    
    LOGS = {
        "google-argon": "https://ct.googleapis.com/log/argon2024/",
        "google-xenon": "https://ct.googleapis.com/log/xenon2024/",
        "digicert-ct1": "https://ct1.digicert-ct.com/log/",
        "letsencrypt-clang": "https://clang.ct.letsencrypt.org/submissions/",
    }
    
    def __init__(self, log_name: str = "google-argon", start_index: int = 0):
        if httpx is None:
            raise ImportError("httpx not installed. Run: pip install httpx")
        
        self.log_url = self.LOGS.get(log_name, list(self.LOGS.values())[0])
        self.start_index = start_index
    
    async def stream_range(
        self, start_index: int, end_index: int
    ) -> AsyncGenerator[CertEvent, None]:
        """
        Poll CT log for entries in [start_index, end_index).
        Fetches entries in batches of 128.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            current = start_index
            batch_size = 128
            
            while current < end_index:
                batch_end = min(current + batch_size, end_index)
                
                try:
                    # Fetch entries from CT log
                    url = f"{self.log_url}ct/v1/get-entries?start={current}&end={batch_end}"
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    data = response.json()
                    entries = data.get("entries", [])
                    
                    for entry in entries:
                        try:
                            event = self._parse_entry(entry)
                            if event:
                                yield event
                        except Exception as e:
                            logger.warning(f"Failed to parse CT log entry: {e}")
                    
                    current = batch_end
                
                except Exception as e:
                    logger.error(f"Failed to fetch CT log range [{current}, {batch_end}): {e}")
                    await asyncio.sleep(5)  # Backoff before retry
    
    def _parse_entry(self, entry: dict) -> Optional[CertEvent]:
        """Parse a CT log entry JSON into a CertEvent."""
        # This is simplified; full implementation would decode X.509 from entry["leaf_input"]
        # For MVP, we extract metadata if available
        
        try:
            # In production:
            # - Decode entry["leaf_input"] (base64) to get X.509 cert
            # - Extract subject, issuer, SANs, dates
            # - Return CertEvent
            
            # For now, return None to skip (would need pyasn1/cryptography to decode X.509)
            return None
        except Exception as e:
            logger.debug(f"Could not parse CT log entry: {e}")
            return None
