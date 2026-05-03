const streamTable = document.getElementById("stream-table");
const statusIndicator = document.getElementById("status");
const maxRows = 50;

function connectSSE() {
    // Connects to FastAPI SSE endpoint
    const evtSource = new EventSource("/stream");
    
    evtSource.onopen = () => {
        statusIndicator.textContent = "🟢 Connected (Live)";
        statusIndicator.style.color = "#4aff8b";
    };

    evtSource.onmessage = (event) => {
        const verdict = JSON.parse(event.data);
        
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

async function analyzeDomain() {
    const input = document.getElementById("domain-input").value;
    const resultBox = document.getElementById("analysis-result");
    
    if (!input) return;
    
    resultBox.textContent = "Analyzing latency targets (<2ms)...";
    
    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: input})
        });
        
        const data = await response.json();
        resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        resultBox.textContent = "Error connecting to CTMonitor API: " + e.message;
    }
}

// Initial connection
connectSSE();