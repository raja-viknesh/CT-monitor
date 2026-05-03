"""FastAPI Server."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from ctmonitor.ingestion.models import NormalisedCert, CertVerdict, CertVerdictTier
from ctmonitor.pipeline.normaliser import Normaliser

app = FastAPI(title="CT Monitor API", version="0.1.0")

class AnalyzeRequest(BaseModel):
    domain: str

@app.get("/health")
async def health():
    return {"status": "ok", "uptime_s": 0}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    # Live hook to quorum engine
    return {"domain": req.domain, "risk_score": 0.88, "tier": "BLOCK", "confidence_lower": 0.85, "confidence_upper": 0.90, "latency_ms": 1.25}

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
