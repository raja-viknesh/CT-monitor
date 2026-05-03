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
    const heatContainer = document.getElementById("heatmap-container");
    
    if (!input) return;
    
    resultBox.textContent = "Analyzing latency targets (<2ms)...";
    heatContainer.innerHTML = ""; // Clear heatmap
    
    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: input})
        });
        
        const data = await response.json();
        
        // Render Heatmap dynamically
        if(data.detector_results) {
            data.detector_results.forEach(det => {
                const heat = det.score * 100;
                let color = "#4aff8b"; // Safe
                if(heat > 35) color = "#4aa1ff";
                if(heat > 60) color = "#ffb84a";
                if(heat > 85) color = "#ff4a4a"; // Danger
                
                heatContainer.innerHTML += `
                    <div style="flex: 1; text-align: center; background: #222; border: 1px solid ${color}; border-radius: 4px; padding: 10px;">
                        <div style="font-size: 0.75em; color: #888;">${det.detector_name.replace('Detector','')}</div>
                        <div style="font-size: 1.2em; font-weight: bold; color: ${color}">${heat.toFixed(1)}%</div>
                        <div style="font-size: 0.7em; color: #666;">${det.latency_ms.toFixed(2)}ms</div>
                    </div>
                `;
            });
        }
        
        resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
        resultBox.textContent = "Error connecting to CTMonitor API: " + e.message;
    }
}

// Initial connection
connectSSE();