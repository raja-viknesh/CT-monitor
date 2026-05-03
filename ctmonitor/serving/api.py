"""FastAPI Server."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from sse_starlette.sse import EventSourceResponse

from ctmonitor.ingestion.models import NormalisedCert, CertVerdict, CertVerdictTier
from ctmonitor.pipeline.normaliser import Normaliser
# (Pretending quorum engine is loaded properly in full build)

app = FastAPI(title="CT Monitor API", version="0.1.0")

class AnalyzeRequest(BaseModel):
    domain: str

@app.get("/health")
async def health():
    return {"status": "ok", "uptime_s": 0}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    # Dummy integration
    return {"domain": req.domain, "risk_score": 0.0, "tier": "SAFE"}

# Static files for dashboard
# app.mount("/dashboard", StaticFiles(directory="ctmonitor/dashboard", html=True), name="dashboard")
