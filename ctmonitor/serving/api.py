"""FastAPI Server."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import dataclasses
from urllib.parse import urlparse
from sse_starlette.sse import EventSourceResponse
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone

from ctmonitor.ingestion.models import NormalisedCert, CertVerdict, CertVerdictTier, CertEvent
from ctmonitor.pipeline.normaliser import Normaliser
from ctmonitor.quorum.engine import QuorumEngine
from ctmonitor.detectors.heuristic.levenshtein import LevenshteinDetector
from ctmonitor.detectors.heuristic.tld_keyword import TLDKeywordDetector
from ctmonitor.detectors.heuristic.homograph import HomographDetector

app = FastAPI(title="CT Monitor API", version="0.1.0")

# Initialize Engine
normaliser = Normaliser()
engine = QuorumEngine(detectors=[
    LevenshteinDetector(),
    TLDKeywordDetector(),
    HomographDetector()
])

class AnalyzeRequest(BaseModel):
    domain: str

@app.get("/health")
async def health():
    return {"status": "ok", "uptime_s": 0}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    # Extract domain if full URL is pasted (e.g. from browser extension)
    raw_domain = req.domain.strip()
    if raw_domain.startswith("http"):
        raw_domain = urlparse(raw_domain).netloc

    # Create dummy CertEvent for immediate analysis
    event = CertEvent(
        domain=raw_domain,
        san_list=[raw_domain],
        issuer_cn="Local Request",
        org=None,
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc),
        log_id="manual",
        fingerprint_sha256="000"
    )
    
    norm_cert = normaliser.process(event)
    verdict = engine.evaluate(norm_cert)
    
    # Return serializable dict
    return dataclasses.asdict(verdict)

@app.get("/stream")
async def stream():
    """SSE Endpoint for Server-Sent Events to push verdicts live."""
    async def event_generator():
        while True:
            await asyncio.sleep(2)  # Mock pacing for local test
            # Yield dummy payload matching the CertVerdict footprint
            payload = {"domain": "mock-stream-paypal.com", "risk_score": 0.91, "tier": "BLOCK"}
            yield {"event": "message", "data": payload}

    return EventSourceResponse(event_generator())

# Mount Vanilla JS dashboard at root
dashboard_path = Path(__file__).parent.parent / "dashboard"
app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")
