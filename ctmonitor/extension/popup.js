function setOfflineMode(message) {
    document.getElementById("score-display").textContent = "Local API Offline";
    document.getElementById("tier-display").textContent = "Tier: N/A";
    document.getElementById("analysis-preview").textContent = message;
}

function topContributions(verdict, topN = 3) {
    const rows = (verdict.detector_results || [])
        .map((d) => ({
            name: d.detector_name,
            weighted: (Number(d.score) || 0) * (Number(d.confidence) || 0),
            score: Number(d.score) || 0,
            confidence: Number(d.confidence) || 0,
        }))
        .sort((a, b) => b.weighted - a.weighted)
        .slice(0, topN);
    return rows;
}

function downloadJSONReport(domain, verdict) {
    const payload = JSON.stringify(verdict, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ctmonitor-report-${domain}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
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
    const contributions = topContributions(verdict, 3)
        .map((c) => `${c.name}: ${(c.weighted * 100).toFixed(1)} weighted`)
        .join(" | ");
    preview.textContent = [
        `Report for ${domain}`,
        `Mode: ${verdict.analysis_mode || "extension-local"}`,
        `Belief: ${(summary.belief_threat ?? verdict.combined_belief ?? 0).toFixed(3)}`,
        `Plausibility: ${(summary.plausibility_threat ?? verdict.combined_plausibility ?? 0).toFixed(3)}`,
        `Signals: ${reasoning.slice(0, 3).join(" | ") || "No notable signals"}`,
        `Contrib: ${contributions || "N/A"}`
    ].join("\n");

    document.getElementById("reanalyze-btn").onclick = () => {
        chrome.runtime.sendMessage({type: "reanalyze-domain", domain, tabId}, () => window.close());
    };

    document.getElementById("download-report-btn").onclick = async () => {
        if (verdict.analysis_mode === "extension-local") {
            downloadJSONReport(domain, verdict);
            return;
        }

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
            downloadJSONReport(domain, verdict);
        }
    };

    document.getElementById("view-report-btn").onclick = () => {
        chrome.runtime.sendMessage({type: "open-report", domain}, () => {});
        window.close();
    };

    document.getElementById("settings-btn").onclick = () => {
        chrome.runtime.openOptionsPage();
        window.close();
    };
}

function buildLocalVerdict(domain) {
    const verdict = CTLocalEngine.analyzeDomain(domain);
    verdict.analysis_mode = "extension-local";
    verdict.generated_at = new Date().toISOString();
    return verdict;
}

chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    const tab = tabs[0];
    let domain = "";
    try {
        const url = new URL(tab.url);
        domain = url.hostname;
    } catch {
        document.getElementById("domain-name").textContent = "Unsupported tab URL";
        setOfflineMode("CTMonitor can only analyze http/https pages.");
        return;
    }

    document.getElementById("domain-name").textContent = domain;

    chrome.storage.local.get([tab.id.toString(), domain, `${tab.id.toString()}::backend`, `${domain}::backend`], (result) => {
        const verdict = result[tab.id.toString()];
        const domainVerdict = result[domain];
        const bestVerdict = verdict || domainVerdict;
        if (bestVerdict) {
            renderVerdict(bestVerdict, domain, tab.id);
        } else {
            const localVerdict = buildLocalVerdict(domain);
            chrome.storage.local.set({
                [tab.id.toString()]: localVerdict,
                [domain]: localVerdict,
            });
            renderVerdict(localVerdict, domain, tab.id);
            document.getElementById("reanalyze-btn").onclick = () => {
                chrome.runtime.sendMessage({type: "reanalyze-domain", domain, tabId: tab.id}, () => window.close());
            };
        }

        fetchBackendStatus().then((status) => {
            if (status.status === "down" && !bestVerdict) {
                setOfflineMode("CTMonitor can analyze locally. Backend enrichment is currently unavailable.");
            }
        });
    });
});