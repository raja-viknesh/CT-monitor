"""Certstream WebSocket consumer for real-time CT log ingestion."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Callable

try:
    import websockets
except ImportError:
    websockets = None

from ctmonitor.ingestion.models import CertEvent
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class CertstreamConsumer:
    """
    Connects to Certstream WebSocket (https://certstream.calidog.io) to ingest
    live certificate events at ~12 certs/sec global rate.
    """
    
    CERTSTREAM_URL = "wss://certstream.calidog.io/full"
    
    def __init__(self):
        if websockets is None:
            raise ImportError("websockets not installed. Run: pip install websockets")
    
    async def stream(self) -> AsyncGenerator[CertEvent, None]:
        """
        Connects to Certstream and yields CertEvent objects.
        Automatically reconnects on failure with exponential backoff.
        """
        backoff = 1
        max_backoff = 60
        
        while True:
            try:
                async with websockets.connect(self.CERTSTREAM_URL, ping_interval=None) as ws:
                    backoff = 1  # Reset backoff on successful connection
                    logger.info("Connected to Certstream WebSocket")
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            
                            # Filter to cert events only (ignore heartbeats)
                            if data.get("message_type") != "certificate_update":
                                continue
                            
                            cert_data = data.get("data", {})
                            cert = cert_data.get("leaf_cert", {})
                            
                            subject = cert.get("subject", {})
                            domain = subject.get("CN", "unknown")
                            
                            san_list = []
                            try:
                                san_str = subject.get("subjectAltName", "")
                                if san_str:
                                    # Parse SAN string: "DNS:example.com, DNS:www.example.com, ..."
                                    for part in san_str.split(", "):
                                        if part.startswith("DNS:"):
                                            san_list.append(part[4:].strip())
                            except Exception as e:
                                logger.warning(f"Failed to parse SAN: {e}")
                            
                            if not san_list:
                                san_list = [domain]
                            
                            issuer = cert.get("issuer", {})
                            issuer_cn = issuer.get("CN", "Unknown CA")
                            
                            org = subject.get("O", None)
                            
                            # Parse validity dates
                            try:
                                not_before = datetime.fromisoformat(
                                    cert.get("not_before", "").replace("Z", "+00:00")
                                )
                            except:
                                not_before = datetime.now(timezone.utc)
                            
                            try:
                                not_after = datetime.fromisoformat(
                                    cert.get("not_after", "").replace("Z", "+00:00")
                                )
                            except:
                                not_after = datetime.now(timezone.utc)
                            
                            fingerprint = cert_data.get("leaf_cert_fingerprint", "")
                            
                            event = CertEvent(
                                domain=domain,
                                san_list=san_list,
                                issuer_cn=issuer_cn,
                                org=org,
                                not_before=not_before,
                                not_after=not_after,
                                log_id=data.get("data", {}).get("log_id", "certstream"),
                                fingerprint_sha256=fingerprint,
                                raw_json={
                                    "message_type": data.get("message_type"),
                                    "timestamp": data.get("timestamp_ms"),
                                }
                            )
                            
                            yield event
                        
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse Certstream message")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing Certstream event: {e}")
                            continue
            
            except Exception as e:
                logger.error(f"Certstream connection failed: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
