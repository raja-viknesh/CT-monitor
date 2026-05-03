chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    if (details.frameId !== 0) return; // Only main frame
    
    try {
        const url = new URL(details.url);
        const domain = url.hostname;
        
        const response = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain})
        });
        
        if (response.ok) {
            const verdict = await response.json();
            // Store under both tabId and hostname so popup and content scripts can sync easily
            chrome.storage.local.set({
                [details.tabId.toString()]: verdict,
                [domain]: verdict
            });
            
            if (verdict.tier !== "SAFE") {
                let color = verdict.tier === "BLOCK" ? "#E24B4A" : (verdict.tier === "WARN" ? "#EF9F27" : "#378ADD");
                chrome.action.setBadgeBackgroundColor({color, tabId: details.tabId});
                chrome.action.setBadgeText({text: Math.round(verdict.risk_score * 100).toString(), tabId: details.tabId});
            }
        }
    } catch (e) {
        console.error("CTMonitor engine unreachable", e);
    }
});