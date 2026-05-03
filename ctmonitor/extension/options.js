const SETTINGS_KEY = "__ctmonitor_settings";
const BACKEND_STATUS_KEY = "__ctmonitor_backend_status";

const defaults = {
    backendEnrichment: false,
    notifications: true,
    blockInterstitial: true,
};

function setStatus(message, ok = true) {
    const node = document.getElementById("status");
    node.textContent = message;
    node.className = ok ? "ok" : "muted";
}

function collectUI() {
    return {
        backendEnrichment: document.getElementById("backend-enrichment").checked,
        notifications: document.getElementById("notifications").checked,
        blockInterstitial: document.getElementById("block-interstitial").checked,
    };
}

function applyUI(settings) {
    document.getElementById("backend-enrichment").checked = !!settings.backendEnrichment;
    document.getElementById("notifications").checked = !!settings.notifications;
    document.getElementById("block-interstitial").checked = !!settings.blockInterstitial;
}

async function loadSettings() {
    const data = await chrome.storage.local.get([SETTINGS_KEY]);
    const settings = { ...defaults, ...(data[SETTINGS_KEY] || {}) };
    applyUI(settings);
}

async function saveSettings() {
    const settings = collectUI();
    const response = await chrome.runtime.sendMessage({ type: "update-settings", settings });
    if (response?.ok) {
        setStatus("Settings saved.", true);
    } else {
        setStatus("Failed to save settings.", false);
    }
}

async function clearVerdicts() {
    const all = await chrome.storage.local.get(null);
    const keys = Object.keys(all).filter((k) => {
        if (k === SETTINGS_KEY || k === BACKEND_STATUS_KEY) return false;
        if (k.startsWith("__ctmonitor_pending_block_")) return false;
        if (k.startsWith("__ctmonitor_bypass_")) return false;
        return true;
    });

    if (keys.length > 0) {
        await chrome.storage.local.remove(keys);
    }
    setStatus(`Cleared ${keys.length} stored entries.`, true);
}

document.getElementById("save-btn").addEventListener("click", saveSettings);
document.getElementById("clear-btn").addEventListener("click", clearVerdicts);

loadSettings();
