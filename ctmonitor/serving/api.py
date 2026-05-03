"""FastAPI Server."""

import asyncio
import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ctmonitor.ingestion.models import NormalisedCert, CertVerdict, CertVerdictTier, CertEvent
from ctmonitor.pipeline.normaliser import Normaliser
from ctmonitor.quorum.engine import QuorumEngine
from ctmonitor.detectors.heuristic.levenshtein import LevenshteinDetector
from ctmonitor.detectors.heuristic.tld_keyword import TLDKeywordDetector
from ctmonitor.detectors.heuristic.homograph import HomographDetector

app = FastAPI(title="CT Monitor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine
normaliser = Normaliser()
engine = QuorumEngine(detectors=[
    LevenshteinDetector(),
    TLDKeywordDetector(),
    HomographDetector()
])

class AnalyzeRequest(BaseModel):
    domain: str


def _analyse_domain(raw_domain: str):
    domain = raw_domain.strip()
    if domain.startswith("http"):
        domain = urlparse(domain).netloc

    event = CertEvent(
        domain=domain,
        san_list=[domain],
        issuer_cn="Local Request",
        org=None,
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc),
        log_id="manual",
        fingerprint_sha256="000"
    )

    norm_cert = normaliser.process(event)
    return engine.evaluate(norm_cert)


def _verdict_payload(domain: str):
    verdict = _analyse_domain(domain)
    payload = dataclasses.asdict(verdict)
    payload["analysis_available"] = bool(payload.get("analysis"))
    return payload

@app.get("/health")
async def health():
    return {"status": "ok", "uptime_s": 0}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    return _verdict_payload(req.domain)


@app.get("/api/report")
async def report(domain: str = Query(..., min_length=1)):
    return _verdict_payload(domain)


@app.get("/api/report/download")
async def download_report(domain: str = Query(..., min_length=1)):
    payload = _verdict_payload(domain)
    safe_name = domain.replace("/", "_").replace(":", "_")
    body = json.dumps(jsonable_encoder(payload), indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="ctmonitor-report-{safe_name}.json"'}
    )

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
