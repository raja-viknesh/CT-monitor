# CTMonitor Architectural Progress

## Current Status
- Active phase: Phase 16 (extension completion + end-to-end validation).
- Runtime mode: heuristic + ML detector registry active (ONNX-first wrappers with local fallbacks).
- Local-first guarantee: preserved.

## Build Sequence Tracking
- [x] Phase 1: `ingestion/models.py` dataclasses implemented.
- [x] Phase 2: `pipeline/ring.py` and `pipeline/normaliser.py` implemented.
- [x] Phase 3: `storage/db.py` schema + core CRUD implemented.
- [x] Phase 4: `detectors/base.py` implemented with internal exception handling.
- [x] Phase 5: All 5 heuristic detectors implemented:
  - `levenshtein.py`
  - `homograph.py`
  - `tld_keyword.py`
  - `san_anomaly.py`
  - `domain_age.py`
- [x] Phase 6: `quorum/dempster_shafer.py` implemented.
- [x] Phase 7: `quorum/engine.py` implemented with DS combination + reasoning payload.
- [x] Phase 8: `serving/api.py` implemented with `/health`, `/analyze`, `/stream`, `/api/report`, `/api/report/download`, `/api/stats`, `/api/history`.
- [ ] Phase 9: Dashboard advanced pages pending (currently live stream + manual analysis only).
- [x] Phase 10: `reporter/sarif.py` present and functional.
- [x] Phase 11: `ml/train.py` implemented (artifact-oriented local training entrypoint).
- [x] Phase 12: `ml/export.py` and `ml/inference.py` implemented (ONNX export + ONNX-first inference helper).
- [x] Phase 13: ML detectors implemented and wired into API detector registry.
- [x] Phase 14: `detectors/ml/conformal.py` implemented.
- [ ] Phase 15: Dashboard analytics pages pending.
- [x] Phase 16: Extension core files present and installable; production hardening ongoing.
- [x] Phase 17: `cli.py` command set implemented (`train`, `serve`, `analyze`, `stream`, `export-sarif`, `benchmark`).
- [ ] Phase 18: Full test suite incomplete.

## Success Criteria Completed in This Iteration
- [x] Added missing heuristic detectors (SAN anomaly + domain age).
- [x] Added Certstream ingestion module and API fallback logic.
- [x] Added DB-backed stats/history endpoints.
- [x] Updated architectural progress tracker immediately after goal completion.
- [x] Added ML detector modules (N-gram, VAE, Transformer, Hawkes, GNN) and conformal wrapper.
- [x] Added ONNX-first inference utility and training entrypoint.
- [x] Registered heuristic + ML detectors in serving pipeline.
- [x] Extension works in offline-safe mode when local server is down (clear popup state, no hard failure, graceful reanalysis/download errors).
- [x] Added periodic backend health checks in extension background worker via alarms.
- [x] Added production extension icon assets and wired manifest/action/notification icon paths for clean external installs.

## Next Immediate Targets
1. Harden extension UX for install/use by external users (report routing + permission resilience).
2. Expand dashboard with advanced analysis pages and detector-health visualizations.
3. Complete tests and run full validation.
