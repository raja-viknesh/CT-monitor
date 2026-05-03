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
        const response = await fetch(`http://127.0.0.1:8000/api/report/download?domain=${encodeURIComponent(domain)}`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `ctmonitor-report-${domain}.json`;
        anchor.click();
        URL.revokeObjectURL(url);
    };
}

chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    const tab = tabs[0];
    const url = new URL(tab.url);
    const domain = url.hostname;

    document.getElementById("domain-name").textContent = domain;

    chrome.storage.local.get([tab.id.toString()], (result) => {
        const verdict = result[tab.id.toString()];
        if (verdict) {
            renderVerdict(verdict, domain, tab.id);
        } else {
            document.getElementById("score-display").textContent = "Unscanned";
            document.getElementById("tier-display").textContent = "N/A";
            document.getElementById("analysis-preview").textContent = "The current tab has not been analyzed yet.";
            document.getElementById("reanalyze-btn").onclick = () => {
                chrome.runtime.sendMessage({type: "reanalyze-domain", domain, tabId: tab.id}, () => window.close());
            };
        }
    });
});