"""Training entrypoint for CTMonitor ML detectors (heuristic-safe fallback)."""

from __future__ import annotations

import gzip
import pickle
from pathlib import Path

from ctmonitor.detectors.ml.ngram_lm import CharNgramModel


def download_training_data(data_dir: str = "data") -> dict[str, Path]:
    """Prepare local datasets (placeholder downloader hook)."""
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)

    legit_path = base / "legit_domains_sample.txt"
    if not legit_path.exists():
        legit_path.write_text(
            "google.com\ngithub.com\nopenai.com\npython.org\nmozilla.org\n", encoding="utf-8"
        )

    phish_path = base / "phish_domains_sample.txt"
    if not phish_path.exists():
        phish_path.write_text(
            "paypa1-login.com\nsecure-google-auth.xyz\naccount-verify-amazon.top\n", encoding="utf-8"
        )

    return {"legit": legit_path, "phish": phish_path}


def train_ngram_lm(models_dir: str = "models", force: bool = False) -> Path:
    """Train and persist char ngram model as gzip pickle."""
    model_path = Path(models_dir) / "ngram_4gram.pkl.gz"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if model_path.exists() and not force:
        return model_path

    datasets = download_training_data()
    legit_domains = [line.strip() for line in datasets["legit"].read_text(encoding="utf-8").splitlines() if line.strip()]

    model = CharNgramModel(n=4, k=0.01)
    model.train(legit_domains)

    with gzip.open(model_path, "wb") as fh:
        pickle.dump(model, fh)

    return model_path


def train_vae(models_dir: str = "models", force: bool = False) -> Path:
    """Create VAE artifact placeholder path for ONNX workflow."""
    path = Path(models_dir) / "vae.onnx"
    if not path.exists() or force:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    return path


def train_transformer(models_dir: str = "models", force: bool = False) -> Path:
    """Create transformer artifact placeholder path for ONNX workflow."""
    path = Path(models_dir) / "transformer.onnx"
    if not path.exists() or force:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    return path


def train_gnn(models_dir: str = "models", force: bool = False) -> Path:
    """Create GNN artifact placeholder path."""
    path = Path(models_dir) / "gnn_sage.pt"
    if not path.exists() or force:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    return path


def calibrate_all(models_dir: str = "models") -> Path:
    """Create calibrator directory for future fitted calibrators."""
    path = Path(models_dir) / "calibrators"
    path.mkdir(parents=True, exist_ok=True)
    return path


def train_all(force: bool = False) -> dict[str, str]:
    out = {
        "ngram": str(train_ngram_lm(force=force)),
        "vae": str(train_vae(force=force)),
        "transformer": str(train_transformer(force=force)),
        "gnn": str(train_gnn(force=force)),
        "calibrators": str(calibrate_all()),
    }
    return out
