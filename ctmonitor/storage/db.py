"""SQLite storage layer for persistence and local-first architecture."""

import aiosqlite
import json
from pathlib import Path
from datetime import datetime, timezone

from ctmonitor.ingestion.models import CertVerdict


class DB:
    """Async database operations for local verdict and caching stores."""

    def __init__(self, db_path: str = "ctmonitor.db"):
        self.db_path = Path(db_path)

    async def init_tables(self) -> None:
        """Initialize all tables precisely as per spec."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    tier TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    confidence_lower REAL NOT NULL,
                    confidence_upper REAL NOT NULL,
                    latency_ms REAL NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS whois_cache (
                    domain TEXT PRIMARY KEY,
                    registered_date TEXT,
                    cached_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS brand_watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_name TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    webhook_url TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS allow_list (
                    domain TEXT PRIMARY KEY,
                    added_at TEXT NOT NULL,
                    note TEXT
                )
            """)
            
            # Indexes for stream fetching logic
            await db.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_ts ON verdicts(ts DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_tier ON verdicts(tier)")
            await db.commit()

    async def insert_verdict(self, verdict: CertVerdict) -> None:
        """Store a final quorum verdict."""
        evidence_payload = [
            {
                "detector": res.detector_name,
                "score": res.score,
                "confidence": res.confidence,
                "latency_ms": res.latency_ms,
                "evidence": res.evidence
            } for res in verdict.detector_results
        ]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO verdicts 
                (ts, domain, risk_score, tier, evidence_json, confidence_lower, confidence_upper, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verdict.ts.isoformat(),
                    verdict.domain,
                    verdict.risk_score,
                    verdict.tier.value,
                    json.dumps(evidence_payload),
                    verdict.confidence_lower,
                    verdict.confidence_upper,
                    verdict.latency_ms
                )
            )
            await db.commit()
    
    async def get_verdict(self, domain: str) -> dict | None:
        """Retrieve cached verdict for a domain."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT risk_score, tier, evidence_json, confidence_lower, confidence_upper FROM verdicts WHERE domain = ? ORDER BY ts DESC LIMIT 1",
                (domain,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "risk_score": row[0],
                        "tier": row[1],
                        "evidence": json.loads(row[2]),
                        "confidence_lower": row[3],
                        "confidence_upper": row[4]
                    }
        return None
    
    async def list_recent_verdicts(self, limit: int = 100) -> list[dict]:
        """List recent verdicts."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT domain, risk_score, tier, ts FROM verdicts ORDER BY ts DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"domain": r[0], "risk_score": r[1], "tier": r[2], "ts": r[3]} for r in rows]
    
    async def get_stats(self) -> dict:
        """Get database statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM verdicts") as cursor:
                total = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT tier, COUNT(*) FROM verdicts GROUP BY tier") as cursor:
                rows = await cursor.fetchall()
                by_tier = {row[0]: row[1] for row in rows}
            
            return {"total_verdicts": total, "by_tier": by_tier}
