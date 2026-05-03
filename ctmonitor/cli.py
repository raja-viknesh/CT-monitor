"""Typer CLI Entry."""

import typer
import uvicorn
import asyncio
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def serve():
    console.print("[green]Starting FastAPI server on port 8000[/green]")
    uvicorn.run("ctmonitor.serving.api:app", host="127.0.0.1", port=8000)

@app.command()
def analyze(domain: str):
    console.print(f"Analyzing {domain}...")

if __name__ == "__main__":
    app()
