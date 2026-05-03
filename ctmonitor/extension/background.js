async function analyzeAndStore(domain, tabId) {
    chrome.storage.local.set({
        [domain]: { status: "ANALYZING" },
        [tabId.toString()]: { status: "ANALYZING" }
    });

    chrome.action.setBadgeBackgroundColor({color: "#888888", tabId});
    chrome.action.setBadgeText({text: "...", tabId});

    const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({domain})
    });

    if (!response.ok) {
        throw new Error(`Analysis failed with ${response.status}`);
    }

    const verdict = await response.json();
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

    return verdict;
}

chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return;

    try {
        const url = new URL(details.url);
        await analyzeAndStore(url.hostname, details.tabId);
    } catch (e) {
        console.error("CTMonitor engine unreachable", e);
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

        chrome.tabs.create({url: `http://127.0.0.1:8000/?domain=${encodeURIComponent(message.domain)}`});
        sendResponse({ok: true});
        return false;
    }

    return false;
});
