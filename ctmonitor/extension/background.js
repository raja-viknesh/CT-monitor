const API_BASE = "http://127.0.0.1:8000";
const BACKEND_STATUS_KEY = "__ctmonitor_backend_status";

async function setBackendStatus(status, details = {}) {
    await chrome.storage.local.set({
        [BACKEND_STATUS_KEY]: {
            status,
            checkedAt: new Date().toISOString(),
            ...details,
        },
    });
}

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`, { method: "GET" });
        if (!response.ok) {
            await setBackendStatus("down", { code: response.status });
            return false;
        }
        const payload = await response.json();
        await setBackendStatus("up", { payload });
        return true;
    } catch (error) {
        await setBackendStatus("down", { error: String(error) });
        return false;
    }
}

async function analyzeAndStore(domain, tabId) {
    chrome.storage.local.set({
        [domain]: { status: "ANALYZING" },
        [tabId.toString()]: { status: "ANALYZING" }
    });

    chrome.action.setBadgeBackgroundColor({color: "#888888", tabId});
    chrome.action.setBadgeText({text: "...", tabId});

    const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({domain})
    });

    if (!response.ok) {
        throw new Error(`Analysis failed with ${response.status}`);
    }

    const verdict = await response.json();
    await setBackendStatus("up");
    chrome.storage.local.set({
        [tabId.toString()]: verdict,
        [domain]: verdict
    });

    let color = "#4aff8b";
    if (verdict.tier === "BLOCK") color = "#E24B4A";
    else if (verdict.tier === "WARN") color = "#EF9F27";
    else if (verdict.tier === "WATCH") color = "#378ADD";

    chrome.action.setBadgeBackgroundColor({color, tabId});
    chrome.action.setBadgeText({text: Math.round(verdict.risk_score * 100).toString(), tabId});

    if (verdict.tier === "BLOCK" || verdict.tier === "WARN") {
        const notificationId = `ctmonitor:${tabId}:${domain}`;
        try {
            chrome.notifications.create(notificationId, {
                type: "basic",
                iconUrl: chrome.runtime.getURL("icons/icon128.png"),
                title: `CTMonitor ${verdict.tier}: ${domain}`,
                message: `Risk ${(verdict.risk_score * 100).toFixed(1)}%. Click to open report.`,
                priority: 2,
            });
        } catch (error) {
            // Ignore notification failures (icon/env differences) without breaking analysis.
            console.warn("Notification creation failed", error);
        }
    }

    return verdict;
}

chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return;

    try {
        const url = new URL(details.url);
        await analyzeAndStore(url.hostname, details.tabId);
    } catch (e) {
        console.error("CTMonitor engine unreachable", e);
        await setBackendStatus("down", { error: String(e) });
        const url = new URL(details.url);
        chrome.storage.local.set({ [url.hostname]: { status: "ERROR" } });
        chrome.action.setBadgeBackgroundColor({color: "#E24B4A", tabId: details.tabId});
        chrome.action.setBadgeText({text: "ERR", tabId: details.tabId});
    }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "reanalyze-domain") {
        const tabId = message.tabId ?? sender.tab?.id;
        if (!tabId || !message.domain) {
            sendResponse({ok: false, error: "Missing tabId or domain"});
            return false;
        }

        analyzeAndStore(message.domain, tabId)
            .then((verdict) => sendResponse({ok: true, verdict}))
            .catch((error) => sendResponse({ok: false, error: String(error)}));
        return true;
    }

    if (message?.type === "open-report") {
        if (!message.domain) {
            sendResponse({ok: false, error: "Missing domain"});
            return false;
        }

        checkBackendHealth().then((isUp) => {
            if (isUp) {
                chrome.tabs.create({url: `${API_BASE}/?domain=${encodeURIComponent(message.domain)}`});
                sendResponse({ok: true, route: "dashboard"});
            } else {
                chrome.tabs.create({url: chrome.runtime.getURL("popup.html")});
                sendResponse({ok: true, route: "extension-popup"});
            }
        });
        return true;
    }

    if (message?.type === "backend-health") {
        checkBackendHealth().then((isUp) => sendResponse({ok: true, up: isUp}));
        return true;
    }

    if (message?.type === "get-backend-status") {
        chrome.storage.local.get(BACKEND_STATUS_KEY, (result) => {
            sendResponse({ok: true, status: result[BACKEND_STATUS_KEY] || { status: "unknown" }});
        });
        return false;
    }

    return false;
});

chrome.notifications.onClicked.addListener((notificationId) => {
    if (!notificationId.startsWith("ctmonitor:")) return;
    const parts = notificationId.split(":");
    const domain = parts.slice(2).join(":");
    checkBackendHealth().then((isUp) => {
        if (isUp) {
            chrome.tabs.create({url: `${API_BASE}/?domain=${encodeURIComponent(domain)}`});
        } else {
            chrome.tabs.create({url: chrome.runtime.getURL("popup.html")});
        }
    });
});

chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms.create("ctmonitor-health", { periodInMinutes: 0.5 });
    checkBackendHealth();
});

chrome.runtime.onStartup.addListener(() => {
    chrome.alarms.create("ctmonitor-health", { periodInMinutes: 0.5 });
    checkBackendHealth();
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "ctmonitor-health") {
        checkBackendHealth();
    }
});
