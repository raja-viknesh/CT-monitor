const params = new URLSearchParams(window.location.search);
const domain = (params.get("domain") || "").trim().toLowerCase();
const API_BASE = "http://127.0.0.1:8000";

function weightedContribRows(verdict, topN = 5) {
    return (verdict.detector_results || [])
        .map((d) => ({
            name: d.detector_name,
            weighted: (Number(d.score) || 0) * (Number(d.confidence) || 0),
            score: Number(d.score) || 0,
            confidence: Number(d.confidence) || 0,
        }))
        .sort((a, b) => b.weighted - a.weighted)
        .slice(0, topN);
}

function setText(id, text) {
    const node = document.getElementById(id);
    if (node) node.textContent = text;
}

function tierClass(tier) {
    return ["SAFE", "WATCH", "WARN", "BLOCK"].includes(tier) ? tier : "SAFE";
}

function render(verdict) {
    setText("domain", domain || verdict.domain || "unknown");
    setText("risk", `${((verdict.risk_score || 0) * 100).toFixed(1)}%`);
    setText("interval", `${(verdict.confidence_lower || 0).toFixed(2)} - ${(verdict.confidence_upper || 0).toFixed(2)}`);
    setText("mode", verdict.analysis_mode || "extension-local");
    setText("latency", `${(verdict.latency_ms || 0).toFixed(2)} ms`);

    const tier = document.getElementById("tier");
    tier.className = `badge ${tierClass(verdict.tier)}`;
    tier.textContent = verdict.tier || "SAFE";

    const reasoning = (verdict.analysis && verdict.analysis.reasoning) || [];
    const reasonNode = document.getElementById("reasoning");
    reasonNode.innerHTML = reasoning.length ? reasoning.map((r) => `<div>- ${r}</div>`).join("") : "No reasoning available.";

    const contribNode = document.getElementById("contributions");
    const contribRows = weightedContribRows(verdict, 5);
    contribNode.innerHTML = contribRows.length
        ? contribRows
            .map((r) => `<div>${r.name}: ${(r.weighted * 100).toFixed(1)} weighted (score ${(r.score * 100).toFixed(1)}%, conf ${(r.confidence * 100).toFixed(1)}%)</div>`)
            .join("")
        : "No contribution data.";

    const list = document.getElementById("detectors");
    list.innerHTML = "";
    (verdict.detector_results || []).forEach((det) => {
        const card = document.createElement("div");
        card.className = "card";
        const pct = ((det.score || 0) * 100).toFixed(1);
        card.innerHTML = `<div class=\"muted\">${det.detector_name}</div><div>${pct}%</div><div class=\"muted\">confidence ${(det.confidence || 0).toFixed(2)}</div>`;
        list.appendChild(card);
    });

    document.getElementById("raw").textContent = JSON.stringify(verdict, null, 2);
}

async function getStoredVerdict() {
    if (!domain) return null;
    const data = await chrome.storage.local.get([domain]);
    return data[domain] || null;
}

async function getStoredBackendVerdict() {
    if (!domain) return null;
    const data = await chrome.storage.local.get([`${domain}::backend`]);
    return data[`${domain}::backend`] || null;
}

function downloadVerdict(verdict) {
    const blob = new Blob([JSON.stringify(verdict, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ctmonitor-report-${domain || "domain"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
}

async function analyzeLocalAndStore() {
    if (!domain) return null;
    const verdict = CTLocalEngine.analyzeDomain(domain);
    verdict.analysis_mode = "extension-local";
    verdict.generated_at = new Date().toISOString();
    await chrome.storage.local.set({ [domain]: verdict });
    return verdict;
}

async function tryBackendAnalyze() {
    if (!domain) return null;
    const settingsResp = await chrome.runtime.sendMessage({ type: "get-settings" });
    const settings = settingsResp?.settings || { backendEnrichment: false };
    if (!settings.backendEnrichment) {
        return null;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain }),
            signal: controller.signal,
        });
        if (!response.ok) return null;
        const verdict = await response.json();
        verdict.analysis_mode = "backend";
        await chrome.storage.local.set({ [`${domain}::backend`]: verdict });
        return verdict;
    } catch {
        return null;
    } finally {
        clearTimeout(timer);
    }
}

async function refresh() {
    let verdict = await getStoredVerdict();
    if (!verdict) {
        verdict = await analyzeLocalAndStore();
    }
    if (!verdict) {
        verdict = { domain, tier: "SAFE", risk_score: 0, detector_results: [], analysis: { reasoning: [] } };
    }
    render(verdict);

    let backendVerdict = await getStoredBackendVerdict();
    if (!backendVerdict) {
        backendVerdict = await tryBackendAnalyze();
    }

    if (backendVerdict) {
        const raw = document.getElementById("raw");
        const comparison = {
            primary_local: verdict,
            backend_sample: {
                tier: backendVerdict.tier,
                risk_score: backendVerdict.risk_score,
                detector_count: (backendVerdict.detector_results || []).length,
            },
        };
        raw.textContent = JSON.stringify(comparison, null, 2);
    }

    document.getElementById("download").onclick = () => downloadVerdict(verdict);
    document.getElementById("reanalyze").onclick = async () => {
        const local = await analyzeLocalAndStore();
        render(local);
        const refreshed = await tryBackendAnalyze();
        if (refreshed) render(refreshed);
    };
    document.getElementById("open-dashboard").onclick = () => {
        const url = `${API_BASE}/?domain=${encodeURIComponent(domain)}`;
        chrome.tabs.create({ url });
    };
}

refresh();
