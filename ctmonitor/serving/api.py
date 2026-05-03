"""FastAPI Server."""

import asyncio
import dataclasses
import json
import logging
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
from ctmonitor.detectors.heuristic.san_anomaly import SANAnomalyDetector
from ctmonitor.detectors.heuristic.domain_age import DomainAgeDetector
from ctmonitor.detectors.ml.ngram_lm import NgramLMDetector
from ctmonitor.detectors.ml.vae import VAEDetector
from ctmonitor.detectors.ml.transformer import TransformerDetector
from ctmonitor.detectors.ml.hawkes import HawkesDetector
from ctmonitor.detectors.ml.gnn import GNNDetector
from ctmonitor.storage.db import DB

logger = logging.getLogger(__name__)

app = FastAPI(title="CT Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine with ALL 5 heuristic detectors
normaliser = Normaliser()
detectors = [
    LevenshteinDetector(),
    TLDKeywordDetector(),
    HomographDetector(),
    SANAnomalyDetector(),
    DomainAgeDetector(),
    NgramLMDetector(),
    VAEDetector(),
    TransformerDetector(),
    HawkesDetector(),
    GNNDetector(),
]
engine = QuorumEngine(detectors=detectors)

# Initialize database
db = DB(db_path="ctmonitor.db")

class AnalyzeRequest(BaseModel):
    domain: str


async def _analyse_domain(raw_domain: str):
    """Analyze a domain and return verdict."""
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
    verdict = engine.evaluate(norm_cert)
    
    # Save to database
    try:
        await db.insert_verdict(verdict)
    except Exception as e:
        logger.warning(f"Failed to persist verdict: {e}")
    
    return verdict, verdict.detector_results


def _verdict_payload(domain: str, verdict: CertVerdict):
    """Convert verdict to JSON-serializable format."""
    payload = dataclasses.asdict(verdict)
    payload["tier"] = verdict.tier.value
    payload["ts"] = verdict.ts.isoformat()
    payload["analysis_available"] = bool(payload.get("analysis"))
    payload["detector_count"] = len(verdict.detector_results)
    return payload

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await db.init_tables()
    logger.info("CTMonitor API started (5 heuristic detectors active)")

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "1.0.0", "detectors": [d.name for d in detectors]}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Analyze a domain and return verdict."""
    verdict, detector_results = await _analyse_domain(req.domain)
    return _verdict_payload(req.domain, verdict)


@app.get("/api/report")
async def report(domain: str = Query(..., min_length=1)):
    """Get full report for a domain."""
    verdict, detector_results = await _analyse_domain(domain)
    return _verdict_payload(domain, verdict)

@app.get("/api/report/download")
async def download_report(domain: str = Query(..., min_length=1)):
    """Download report as JSON file."""
    verdict, detector_results = await _analyse_domain(domain)
    payload = _verdict_payload(domain, verdict)
    safe_name = domain.replace("/", "_").replace(":", "_")
    body = json.dumps(jsonable_encoder(payload), indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="ctmonitor-report-{safe_name}.json"'}
    )

@app.get("/api/stats")
async def stats():
    """Get database statistics."""
    return await db.get_stats()

@app.get("/api/history")
async def history(limit: int = Query(100, le=1000)):
    """Get recent verdicts from database."""
    return await db.list_recent_verdicts(limit)

@app.get("/stream")
async def stream():
    """SSE Endpoint for Server-Sent Events with real CT stream if available."""
    async def event_generator():
        # Try to use real Certstream first
        try:
            from ctmonitor.ingestion.stream import CertstreamConsumer
            consumer = CertstreamConsumer()
            async for cert_event in consumer.stream():
                norm_cert = normaliser.process(cert_event)
                verdict = engine.evaluate(norm_cert)
                try:
                    await db.insert_verdict(verdict)
                except:
                    pass
                payload = _verdict_payload(cert_event.domain, verdict)
                yield {"event": "message", "data": json.dumps(jsonable_encoder(payload))}
        except Exception as e:
            logger.warning(f"Certstream unavailable ({e}), falling back to synthetic stream")
            # Fallback: Synthetic stream for offline testing
            sample_domains = [
                "paypal-secure-login.com",
                "devpost.com",
                "xn--pple-43d.com",
                "secure-amazon.example",
                "github-verify.test",
            ]
            index = 0
            while True:
                await asyncio.sleep(2)
                domain = sample_domains[index % len(sample_domains)]
                index += 1
                verdict, _ = await _analyse_domain(domain)
                payload = _verdict_payload(domain, verdict)
                yield {"event": "message", "data": json.dumps(jsonable_encoder(payload))}

    return EventSourceResponse(event_generator())

# Mount Vanilla JS dashboard at root
dashboard_path = Path(__file__).parent.parent / "dashboard"
app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")
