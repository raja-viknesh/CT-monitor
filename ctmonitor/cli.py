"""CTMonitor CLI entry point."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="CTMonitor command line interface")
console = Console()

API_BASE = "http://127.0.0.1:8000"


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Start FastAPI server."""
    console.print(f"[green]Starting CTMonitor API at {host}:{port}[/green]")
    uvicorn.run("ctmonitor.serving.api:app", host=host, port=port)


@app.command()
def analyze(domain: str):
    """One-shot domain analysis."""
    with httpx.Client(timeout=20.0) as client:
        response = client.post(f"{API_BASE}/analyze", json={"domain": domain})
        response.raise_for_status()
        data = response.json()

    table = Table(title=f"Analysis: {data.get('domain', domain)}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Tier", str(data.get("tier")))
    table.add_row("Risk Score", f"{float(data.get('risk_score', 0.0)):.4f}")
    table.add_row("Confidence Lower", f"{float(data.get('confidence_lower', 0.0)):.4f}")
    table.add_row("Confidence Upper", f"{float(data.get('confidence_upper', 0.0)):.4f}")
    table.add_row("Detector Count", str(data.get("detector_count", 0)))
    table.add_row("Latency (ms)", f"{float(data.get('latency_ms', 0.0)):.3f}")
    console.print(table)

    reasoning = (data.get("analysis") or {}).get("reasoning") or []
    if reasoning:
        console.print("\n[bold]Reasoning:[/bold]")
        for item in reasoning:
            console.print(f" - {item}")


@app.command("stream")
def stream_cmd(limit: int = typer.Option(20, min=1, help="Max events to print before exit.")):
    """Read live SSE stream and print verdict events."""
    console.print("[green]Connecting to live stream...[/green]")
    with httpx.Client(timeout=None) as client:
        with client.stream("GET", f"{API_BASE}/stream") as resp:
            resp.raise_for_status()
            count = 0
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    console.print(
                        f"[{data.get('tier','SAFE')}] {data.get('domain','?')} "
                        f"risk={float(data.get('risk_score', 0.0)):.3f}"
                    )
                    count += 1
                    if count >= limit:
                        break


@app.command()
def train(force: bool = typer.Option(False, help="Force retrain existing artifacts.")):
    """Train pipeline entry (currently heuristic/ONNX prep stage)."""
    console.print("[yellow]Training pipeline invoked.[/yellow]")
    console.print(f"force={force}")
    console.print("ML training modules are being staged incrementally in this repository.")


@app.command("export-sarif")
def export_sarif(output: str = "ctmonitor-report.sarif"):
    """Export recent verdict history to SARIF."""
    with httpx.Client(timeout=20.0) as client:
        history = client.get(f"{API_BASE}/api/history", params={"limit": 200}).json()

    # Lightweight conversion from history rows for now
    results = []
    for row in history:
        tier = row.get("tier", "SAFE")
        if tier == "SAFE":
            continue
        level = "error" if tier == "BLOCK" else "warning"
        results.append(
            {
                "ruleId": tier,
                "level": level,
                "message": {"text": f"{row.get('domain')} — risk {float(row.get('risk_score', 0.0)):.2f}"},
                "partialFingerprints": {"attackTechnique": "T1588.004"},
            }
        )

    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [{"tool": {"driver": {"name": "CTMonitor", "version": "1.0.0"}}, "results": results}],
    }

    Path(output).write_text(json.dumps(sarif, indent=2), encoding="utf-8")
    console.print(f"[green]SARIF written:[/green] {output}")


@app.command()
def benchmark(samples: int = typer.Option(100, min=10, help="Number of API calls to benchmark.")):
    """Benchmark end-to-end analysis latency using /analyze endpoint."""
    domain = "devpost.com"
    latencies = []
    with httpx.Client(timeout=20.0) as client:
        for _ in range(samples):
            start = time.perf_counter()
            resp = client.post(f"{API_BASE}/analyze", json={"domain": domain})
            resp.raise_for_status()
            latencies.append((time.perf_counter() - start) * 1000.0)

    latencies.sort()
    p50 = latencies[int(0.50 * len(latencies))]
    p95 = latencies[int(0.95 * len(latencies))]
    p99 = latencies[int(0.99 * len(latencies))]
    mean = sum(latencies) / len(latencies)

    table = Table(title="Benchmark (API end-to-end)")
    table.add_column("Metric", style="cyan")
    table.add_column("Latency ms", style="white")
    table.add_row("mean", f"{mean:.3f}")
    table.add_row("p50", f"{p50:.3f}")
    table.add_row("p95", f"{p95:.3f}")
    table.add_row("p99", f"{p99:.3f}")
    console.print(table)


if __name__ == "__main__":
    app()
