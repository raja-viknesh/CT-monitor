const streamTable = document.getElementById("stream-table");
const statusIndicator = document.getElementById("status");
const maxRows = 50;
let currentReport = null;
let currentDomain = null;

function setCurrentDomain(domain) {
    currentDomain = domain;
    document.getElementById("domain-input").value = domain;
}

function reportUrl(domain) {
    return `/api/report?domain=${encodeURIComponent(domain)}`;
}

function downloadUrl(domain) {
    return `/api/report/download?domain=${encodeURIComponent(domain)}`;
}

function renderReport(data) {
    currentReport = data;

    const summary = data.analysis?.summary || {};
    const reasoning = data.analysis?.reasoning || [];
    const signals = data.analysis?.signals || [];

    document.getElementById("analysis-summary").innerHTML = `
        <strong>${data.domain}</strong><br>
        <span class="muted">Tier: ${data.tier} | Risk: ${(data.risk_score * 100).toFixed(1)}% | Latency: ${data.latency_ms.toFixed(2)}ms</span><br>
        <span class="muted">Belief: ${(summary.belief_threat ?? data.combined_belief).toFixed(3)} | Plausibility: ${(summary.plausibility_threat ?? data.combined_plausibility).toFixed(3)} | Uncertainty: ${(summary.uncertainty ?? 0).toFixed(3)}</span>
    `;

    document.getElementById("reasoning-list").innerHTML = `
        <strong>Reasoning</strong><br>
        ${reasoning.length ? reasoning.map((item) => `<div>• ${item}</div>`).join("") : "<div>No reasoning available.</div>"}
        <div style="margin-top:10px;"><strong>Top signals</strong></div>
        ${signals.length ? signals.map((signal) => `<div class="muted">${signal.detector_name}: score ${signal.score.toFixed(2)}, confidence ${signal.confidence.toFixed(2)}</div>`).join("") : "<div class='muted'>No detector signals.</div>"}
    `;

    document.getElementById("analysis-result").textContent = JSON.stringify(data, null, 2);

    const heatContainer = document.getElementById("heatmap-container");
    heatContainer.innerHTML = "";
    if (data.detector_results) {
        data.detector_results.forEach(det => {
            const heat = det.score * 100;
            let color = "#4aff8b";
            if (heat > 35) color = "#4aa1ff";
            if (heat > 60) color = "#ffb84a";
            if (heat > 85) color = "#ff4a4a";

            heatContainer.innerHTML += `
                <div style="flex: 1; text-align: center; background: #222; border: 1px solid ${color}; border-radius: 4px; padding: 10px;">
                    <div style="font-size: 0.75em; color: #888;">${det.detector_name.replace('Detector','')}</div>
                    <div style="font-size: 1.2em; font-weight: bold; color: ${color}">${heat.toFixed(1)}%</div>
                    <div style="font-size: 0.7em; color: #666;">${det.latency_ms.toFixed(2)}ms</div>
                </div>
            `;
        });
    }
}

function connectSSE() {
    // Connects to FastAPI SSE endpoint
    const evtSource = new EventSource("/stream");
    
    evtSource.onopen = () => {
        statusIndicator.textContent = "🟢 Connected (Live)";
        statusIndicator.style.color = "#4aff8b";
    };

    evtSource.onmessage = (event) => {
        let verdict;
        try {
            verdict = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        } catch (error) {
            console.error("Failed to parse SSE payload", error, event.data);
            return;
        }
        
        const row = document.createElement("tr");
        row.innerHTML = `
            <td style="font-size:0.85em; color:#888;">${new Date().toLocaleTimeString()}</td>
            <td style="font-family: monospace;">${verdict.domain}</td>
            <td>${verdict.risk_score.toFixed(2)}</td>
            <td class="tier-${verdict.tier}">${verdict.tier}</td>
        `;
        
        streamTable.prepend(row);
        if (streamTable.children.length > maxRows) {
            streamTable.removeChild(streamTable.lastChild);
        }
    };

    evtSource.onerror = () => {
        statusIndicator.textContent = "🔴 Reconnecting...";
        statusIndicator.style.color = "#ff4a4a";
        evtSource.close();
        setTimeout(connectSSE, 3000);
    };
}

async function analyzeDomain(domainOverride) {
    const input = domainOverride || document.getElementById("domain-input").value;
    const resultBox = document.getElementById("analysis-result");
    const heatContainer = document.getElementById("heatmap-container");
    
    if (!input) return;
    setCurrentDomain(input);
    
    resultBox.textContent = "Analyzing latency targets (<2ms)...";
    heatContainer.innerHTML = ""; // Clear heatmap
    
    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: input})
        });
        
        const data = await response.json();
        renderReport(data);
    } catch (e) {
        resultBox.textContent = "Error connecting to CTMonitor API: " + e.message;
    }
}

async function reanalyzeDomain() {
    if (!currentDomain) {
        currentDomain = document.getElementById("domain-input").value;
    }
    if (!currentDomain) return;
    await analyzeDomain(currentDomain);
}

async function downloadCurrentReport() {
    if (!currentDomain || !currentReport) return;
    const response = await fetch(downloadUrl(currentDomain));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ctmonitor-report-${currentDomain}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
}

function openCurrentReport() {
    if (!currentDomain) return;
    window.open(`/?domain=${encodeURIComponent(currentDomain)}`, "_blank");
}

async function bootstrapFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const domain = params.get("domain");
    if (domain) {
        setCurrentDomain(domain);
        await analyzeDomain(domain);
    }
}

// Initial connection
connectSSE();
bootstrapFromQuery();