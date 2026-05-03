importScripts("engine.js");

const API_BASE = "http://127.0.0.1:8000";
const BACKEND_STATUS_KEY = "__ctmonitor_backend_status";
const SETTINGS_KEY = "__ctmonitor_settings";
const PENDING_BLOCK_PREFIX = "__ctmonitor_pending_block_";
const BYPASS_PREFIX = "__ctmonitor_bypass_";
const LAST_NOTIFICATION_AT = new Map();
const VERDICT_RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const MAX_STORED_VERDICTS = 3000;

const DEFAULT_SETTINGS = {
    backendEnrichment: false,
    notifications: true,
    blockInterstitial: true,
};

function normalizeDomain(value) {
    if (!value) return "";
    return value.toLowerCase().replace(/:\d+$/, "");
}

function makePendingKey(tabId) {
    return `${PENDING_BLOCK_PREFIX}${tabId}`;
}

function makeBypassKey(tabId) {
    return `${BYPASS_PREFIX}${tabId}`;
}

function isPrivateIPv4(host) {
    const m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (!m) return false;
    const a = Number(m[1]);
    const b = Number(m[2]);
    if (a === 10 || a === 127) return true;
    if (a === 192 && b === 168) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    return false;
}

function isSensitiveDomain(host) {
    if (!host) return true;
    if (host === "localhost") return true;
    if (host.endsWith(".local")) return true;
    if (!host.includes(".")) return true;
    if (isPrivateIPv4(host)) return true;
    return false;
}

function shouldUseBackendForDomain(domain) {
    return !isSensitiveDomain(domain);
}

function parseVerdictTimestamp(value) {
    if (!value || typeof value !== "object") return 0;
    const ts = value.generated_at || value.ts;
    if (!ts || typeof ts !== "string") return 0;
    const t = Date.parse(ts);
    return Number.isFinite(t) ? t : 0;
}

async function getSettings() {
    const result = await chrome.storage.local.get([SETTINGS_KEY]);
    return { ...DEFAULT_SETTINGS, ...(result[SETTINGS_KEY] || {}) };
}

async function setSettings(partial) {
    const current = await getSettings();
    const next = { ...current, ...(partial || {}) };
    await chrome.storage.local.set({ [SETTINGS_KEY]: next });
    return next;
}

async function ensureSettings() {
    const settings = await getSettings();
    await chrome.storage.local.set({ [SETTINGS_KEY]: settings });
}

async function pruneStorage() {
    const all = await chrome.storage.local.get(null);
    const now = Date.now();
    const removable = [];
    const verdictKeys = [];

    for (const [key, value] of Object.entries(all)) {
        if (
            key === BACKEND_STATUS_KEY ||
            key === SETTINGS_KEY ||
            key.startsWith(PENDING_BLOCK_PREFIX) ||
            key.startsWith(BYPASS_PREFIX)
        ) {
            continue;
        }

        if (value && typeof value === "object") {
            const ts = parseVerdictTimestamp(value);
            if (ts > 0) {
                verdictKeys.push({ key, ts });
                if (now - ts > VERDICT_RETENTION_MS) {
                    removable.push(key);
                }
            }
        }
    }

    if (removable.length > 0) {
        await chrome.storage.local.remove(removable);
    }

    if (verdictKeys.length > MAX_STORED_VERDICTS) {
        verdictKeys.sort((a, b) => b.ts - a.ts);
        const overflow = verdictKeys.slice(MAX_STORED_VERDICTS).map((v) => v.key);
        if (overflow.length > 0) {
            await chrome.storage.local.remove(overflow);
        }
    }
}

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

async function fetchBackendVerdict(domain) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2500);
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain }),
            signal: controller.signal,
        });
        if (!response.ok) {
            throw new Error(`Analysis failed with ${response.status}`);
        }
        await setBackendStatus("up");
        return await response.json();
    } catch (error) {
        await setBackendStatus("down", { error: String(error) });
        return null;
    } finally {
        clearTimeout(timer);
    }
}

function setBadge(tabId, verdict) {
    let color = "#4aff8b";
    if (verdict.tier === "BLOCK") color = "#E24B4A";
    else if (verdict.tier === "WARN") color = "#EF9F27";
    else if (verdict.tier === "WATCH") color = "#378ADD";

    chrome.action.setBadgeBackgroundColor({ color, tabId });
    chrome.action.setBadgeText({ text: Math.round((verdict.risk_score || 0) * 100).toString(), tabId });
}

function shouldNotify(domain, tier) {
    if (tier !== "BLOCK" && tier !== "WARN") return false;
    const now = Date.now();
    const last = LAST_NOTIFICATION_AT.get(domain) || 0;
    if (now - last < 120000) return false;
    LAST_NOTIFICATION_AT.set(domain, now);
    return true;
}

function notifyVerdict(domain, tabId, verdict) {
    if (!verdict || typeof verdict.risk_score !== "number") return;
    if (!shouldNotify(domain, verdict.tier)) return;

    const notificationId = `ctmonitor:${tabId}:${domain}`;
    try {
        chrome.notifications.create(notificationId, {
            type: "basic",
            iconUrl: chrome.runtime.getURL("icons/icon128.png"),
            title: `CTMonitor ${verdict.tier}: ${domain}`,
            message: `Risk ${(verdict.risk_score * 100).toFixed(1)}%. Click to open report.`,
            priority: 2,
        });
    } catch (_) {
        // Ignore notification environment issues.
    }
}

async function analyzeAndStore(domain, tabId, pageUrl) {
    const settings = await getSettings();

    await chrome.storage.local.set({
        [domain]: { status: "ANALYZING" },
        [tabId.toString()]: { status: "ANALYZING" },
    });

    chrome.action.setBadgeBackgroundColor({ color: "#888888", tabId });
    chrome.action.setBadgeText({ text: "...", tabId });

    const localVerdict = CTLocalEngine.analyzeDomain(domain);
    localVerdict.analysis_mode = "extension-local";
    localVerdict.generated_at = new Date().toISOString();

    await chrome.storage.local.set({
        [tabId.toString()]: localVerdict,
        [domain]: localVerdict,
    });

    setBadge(tabId, localVerdict);

    if (settings.notifications) {
        notifyVerdict(domain, tabId, localVerdict);
    }

    if (settings.blockInterstitial && localVerdict.tier === "BLOCK" && pageUrl) {
        await chrome.storage.local.set({
            [makePendingKey(tabId)]: {
                domain,
                url: pageUrl,
                createdAt: new Date().toISOString(),
            },
        });

        const blockUrl = chrome.runtime.getURL(
            `block.html?tabId=${encodeURIComponent(String(tabId))}&domain=${encodeURIComponent(domain)}`
        );
        await chrome.tabs.update(tabId, { url: blockUrl });
    }

    if (!settings.backendEnrichment || !shouldUseBackendForDomain(domain)) {
        return localVerdict;
    }

    fetchBackendVerdict(domain)
        .then(async (backendVerdict) => {
            if (!backendVerdict) return;

            const enriched = {
                ...backendVerdict,
                analysis_mode: "backend",
                local_fallback: localVerdict,
            };

            await chrome.storage.local.set({
                [`${tabId.toString()}::backend`]: enriched,
                [`${domain}::backend`]: enriched,
            });

            if (settings.notifications && enriched.tier === "BLOCK" && localVerdict.tier !== "BLOCK") {
                notifyVerdict(domain, tabId, enriched);
            }
        })
        .catch(() => {});

    return localVerdict;
}

async function shouldBypassBlock(tabId, url) {
    const key = makeBypassKey(tabId);
    const result = await chrome.storage.local.get([key]);
    const entry = result[key];

    if (!entry || entry.url !== url) {
        return false;
    }

    const created = Date.parse(entry.createdAt || "");
    if (!Number.isFinite(created) || Date.now() - created > 2 * 60 * 1000) {
        await chrome.storage.local.remove([key]);
        return false;
    }

    await chrome.storage.local.remove([key]);
    return true;
}

chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return;

    try {
        const url = new URL(details.url);
        if (url.protocol !== "http:" && url.protocol !== "https:") return;
        if (!url.hostname) return;

        if (await shouldBypassBlock(details.tabId, details.url)) {
            await analyzeAndStore(normalizeDomain(url.hostname), details.tabId, "");
            return;
        }

        await analyzeAndStore(normalizeDomain(url.hostname), details.tabId, details.url);
    } catch (error) {
        await setBackendStatus("down", { error: String(error) });
    }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "reanalyze-domain") {
        const tabId = message.tabId ?? sender.tab?.id;
        const domain = normalizeDomain(message.domain);

        if (!tabId || !domain) {
            sendResponse({ ok: false, error: "Missing tabId or domain" });
            return false;
        }

        analyzeAndStore(domain, tabId, "")
            .then((verdict) => sendResponse({ ok: true, verdict }))
            .catch((error) => sendResponse({ ok: false, error: String(error) }));
        return true;
    }

    if (message?.type === "open-report") {
        const domain = normalizeDomain(message.domain);
        if (!domain) {
            sendResponse({ ok: false, error: "Missing domain" });
            return false;
        }

        const report = chrome.runtime.getURL(`report.html?domain=${encodeURIComponent(domain)}`);
        chrome.tabs.create({ url: report }, () => {
            sendResponse({ ok: true, route: "extension-report" });
        });
        return true;
    }

    if (message?.type === "get-settings") {
        getSettings().then((settings) => sendResponse({ ok: true, settings }));
        return true;
    }

    if (message?.type === "update-settings") {
        setSettings(message.settings || {}).then((settings) => sendResponse({ ok: true, settings }));
        return true;
    }

    if (message?.type === "get-pending-block") {
        const tabId = Number(message.tabId);
        if (!Number.isFinite(tabId)) {
            sendResponse({ ok: false, error: "Invalid tabId" });
            return false;
        }

        const key = makePendingKey(tabId);
        chrome.storage.local.get([key], (result) => {
            sendResponse({ ok: true, pending: result[key] || null });
        });
        return true;
    }

    if (message?.type === "continue-block-navigation") {
        const tabId = Number(message.tabId);
        if (!Number.isFinite(tabId)) {
            sendResponse({ ok: false, error: "Invalid tabId" });
            return false;
        }

        const key = makePendingKey(tabId);
        chrome.storage.local.get([key], async (result) => {
            const pending = result[key];
            if (!pending?.url) {
                sendResponse({ ok: false, error: "No pending navigation" });
                return;
            }

            await chrome.storage.local.set({
                [makeBypassKey(tabId)]: {
                    url: pending.url,
                    createdAt: new Date().toISOString(),
                },
            });

            await chrome.storage.local.remove([key]);
            await chrome.tabs.update(tabId, { url: pending.url });
            sendResponse({ ok: true });
        });
        return true;
    }

    if (message?.type === "dismiss-block-navigation") {
        const tabId = Number(message.tabId);
        if (!Number.isFinite(tabId)) {
            sendResponse({ ok: false, error: "Invalid tabId" });
            return false;
        }

        chrome.storage.local.remove([makePendingKey(tabId)], () => sendResponse({ ok: true }));
        return true;
    }

    if (message?.type === "backend-health") {
        checkBackendHealth().then((isUp) => sendResponse({ ok: true, up: isUp }));
        return true;
    }

    if (message?.type === "get-backend-status") {
        chrome.storage.local.get(BACKEND_STATUS_KEY, (result) => {
            sendResponse({ ok: true, status: result[BACKEND_STATUS_KEY] || { status: "unknown" } });
        });
        return false;
    }

    return false;
});

chrome.notifications.onClicked.addListener((notificationId) => {
    if (!notificationId.startsWith("ctmonitor:")) return;
    const parts = notificationId.split(":");
    const domain = parts.slice(2).join(":");
    const report = chrome.runtime.getURL(`report.html?domain=${encodeURIComponent(domain)}`);
    chrome.tabs.create({ url: report });
});

chrome.runtime.onInstalled.addListener(() => {
    chrome.alarms.create("ctmonitor-health", { periodInMinutes: 0.5 });
    chrome.alarms.create("ctmonitor-prune", { periodInMinutes: 60 });
    ensureSettings();
    checkBackendHealth();
    pruneStorage();
});

chrome.runtime.onStartup.addListener(() => {
    chrome.alarms.create("ctmonitor-health", { periodInMinutes: 0.5 });
    chrome.alarms.create("ctmonitor-prune", { periodInMinutes: 60 });
    ensureSettings();
    checkBackendHealth();
    pruneStorage();
});

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "ctmonitor-health") {
        checkBackendHealth();
        return;
    }

    if (alarm.name === "ctmonitor-prune") {
        pruneStorage();
    }
});
