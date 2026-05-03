# CTMonitor: Research Prototype for Local-First CT Threat Detection

CTMonitor is a research-oriented prototype for studying how Certificate Transparency (CT) telemetry can be used to detect phishing, typosquatting, and suspicious TLS certificate issuance with minimal latency. The reduced public repository presents the project as a browser-extension-centered system with optional local backend enrichment, calibrated scoring, and explainable verdict output.

## Abstract

Certificate Transparency logs provide a high-volume stream of newly issued certificates. This project explores whether CT-derived features can be used to identify suspicious domains at navigation time, without relying on cloud services. The core emphasis is on local-first operation, transparent detector outputs, and browser-native decision surfaces.


## System Overview

- **Extension-local inference:** The browser extension evaluates domains locally through a JavaScript detector engine.
- **Optional backend enrichment:** A local Python backend can enrich verdicts when available.
- **Explainability:** Verdicts expose tier, risk score, detector breakdown, and weighted contributions.
- **User interaction:** Popup, report, notification, and interstitial flows provide immediate feedback.

## Deployment

### Extension-Only Mode

1. Open `chrome://extensions` in Chrome or Edge.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select the `ctmonitor/extension` folder from this repository.


## Experimental

This repository is best understood as a prototype for iterative evaluation rather than a finished product.

- **Inputs:** domain names, certificate metadata, and browser navigation events.
- **Outputs:** SAFE, WATCH, WARN, and BLOCK verdicts with confidence and evidence summaries.
- **Deployment modes:** extension-only baseline or extension plus optional local backend.

## Repository Contents

The current codebase centers on the browser extension and its supporting artifacts.

- `ctmonitor/extension/manifest.json`
- `ctmonitor/extension/background.js`
- `ctmonitor/extension/engine.js`
- `ctmonitor/extension/content.js`
- `ctmonitor/extension/popup.html`
- `ctmonitor/extension/popup.js`
- `ctmonitor/extension/report.html`
- `ctmonitor/extension/report.js`
- `ctmonitor/extension/options.html`
- `ctmonitor/extension/options.js`
- `ctmonitor/extension/block.html`
- `ctmonitor/extension/block.js`

Other workspace files reflect backend and research scaffolding used during development.

## Extension Behavior

1. On navigation, the worker evaluates the current domain locally.
2. Verdicts are stored in `chrome.storage`.
3. WARN and BLOCK verdicts surface via badges, notifications, and the content-script banner.
4. BLOCK verdicts can trigger a safety interstitial with continue/dismiss controls.
5. The report view shows detector outputs and the strongest weighted contributions.

## Privacy and Safety Considerations

- Local analysis is the default behavior.
- Backend enrichment is optional and can be disabled in settings.
- Private or sensitive hostnames are treated conservatively.
- Stored verdicts are pruned over time to reduce retention.


