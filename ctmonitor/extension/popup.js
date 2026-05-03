function setOfflineMode(message) {
    document.getElementById("score-display").textContent = "Local API Offline";
    document.getElementById("tier-display").textContent = "Tier: N/A";
    document.getElementById("analysis-preview").textContent = message;
}

function fetchBackendStatus() {
    return new Promise((resolve) => {
        chrome.runtime.sendMessage({ type: "get-backend-status" }, (response) => {
            if (chrome.runtime.lastError || !response?.ok) {
                resolve({ status: "unknown" });
                return;
            }
            resolve(response.status || { status: "unknown" });
        });
    });
}

function renderVerdict(verdict, domain, tabId) {
    document.getElementById("score-display").textContent = (verdict.risk_score * 100).toFixed(1) + "% Risk";
    document.getElementById("tier-display").textContent = "Tier: " + verdict.tier;
    document.getElementById("tier-display").className = verdict.tier;
    document.getElementById("score-display").className = "score " + verdict.tier;

    const preview = document.getElementById("analysis-preview");
    const summary = verdict.analysis?.summary || {};
    const reasoning = verdict.analysis?.reasoning || [];
    preview.textContent = [
        `Report for ${domain}`,
        `Belief: ${(summary.belief_threat ?? verdict.combined_belief ?? 0).toFixed(3)}`,
        `Plausibility: ${(summary.plausibility_threat ?? verdict.combined_plausibility ?? 0).toFixed(3)}`,
        `Signals: ${reasoning.slice(0, 3).join(" | ") || "No notable signals"}`
    ].join("\n");

    document.getElementById("reanalyze-btn").onclick = () => {
        chrome.runtime.sendMessage({type: "reanalyze-domain", domain, tabId}, () => window.close());
    };

    document.getElementById("download-report-btn").onclick = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/report/download?domain=${encodeURIComponent(domain)}`);
            if (!response.ok) {
                throw new Error(`download failed: ${response.status}`);
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `ctmonitor-report-${domain}.json`;
            anchor.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            setOfflineMode("CTMonitor local server is offline. Start it with: ctmonitor serve");
        }
    };
}

chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    const tab = tabs[0];
    const url = new URL(tab.url);
    const domain = url.hostname;

    document.getElementById("domain-name").textContent = domain;

    fetchBackendStatus().then((status) => {
        if (status.status === "down") {
            setOfflineMode("Local server not reachable. Start: ctmonitor serve\nYou can still browse; live analysis resumes automatically when server is up.");
        }
    });

    chrome.storage.local.get([tab.id.toString()], (result) => {
        const verdict = result[tab.id.toString()];
        if (verdict) {
            renderVerdict(verdict, domain, tab.id);
        } else {
            document.getElementById("score-display").textContent = "Unscanned";
            document.getElementById("tier-display").textContent = "N/A";
            document.getElementById("analysis-preview").textContent = "The current tab has not been analyzed yet.";
            document.getElementById("reanalyze-btn").onclick = () => {
                chrome.runtime.sendMessage({type: "reanalyze-domain", domain, tabId: tab.id}, (response) => {
                    if (chrome.runtime.lastError || !response?.ok) {
                        setOfflineMode("Reanalysis failed because local server is offline. Start: ctmonitor serve");
                        return;
                    }
                    window.close();
                });
            };
        }
    });
});