# CTMonitor Extension

Manifest V3 browser extension for local-first phishing and typosquatting risk warnings.

## Included

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
- `ctmonitor/extension/icons/*`

## Load In Chrome

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select `ctmonitor/extension`.

## Runtime Modes

- Extension-local mode (default): local JS detector engine only.
- Backend enrichment (optional): can call `http://127.0.0.1:8000` if enabled in Settings.

## Privacy Defaults

- Backend enrichment: off by default
- Notifications: on
- BLOCK interstitial: on
- Local verdict retention pruning enabled

## Notes

- Local workspace files outside extension are intentionally kept on disk.
- Git tracking is configured to include extension files only.
