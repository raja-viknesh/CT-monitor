// Content script for CTMonitor
// Injects a warning banner if the page is blocked or warned

function showBanner(verdict) {
    if (document.getElementById("ctmonitor-banner")) return;
    
    const banner = document.createElement("div");
    banner.id = "ctmonitor-banner";
    banner.style.position = "fixed";
    banner.style.top = "0";
    banner.style.left = "0";
    banner.style.width = "100%";
    banner.style.backgroundColor = verdict.tier === "BLOCK" ? "#E24B4A" : "#EF9F27";
    banner.style.color = "white";
    banner.style.textAlign = "center";
    banner.style.padding = "12px";
    banner.style.zIndex = "999999999";
    banner.style.fontFamily = "sans-serif";
    banner.style.fontWeight = "bold";
    banner.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
    banner.innerHTML = `⚠️ CTMonitor Flagged this page (${verdict.tier}). Risk Score: ${(verdict.risk_score * 100).toFixed(1)}%. <span style="cursor:pointer; text-decoration:underline; margin-left: 15px;" id="ctmonitor-dismiss">Dismiss</span>`;
    
    document.body.prepend(banner);
    
    document.getElementById("ctmonitor-dismiss").addEventListener("click", () => {
        banner.remove();
    });
}

// Check if already injected
chrome.storage.local.get(window.location.hostname, (items) => {
    const verdict = items[window.location.hostname];
    if (verdict && (verdict.tier === "BLOCK" || verdict.tier === "WARN")) {
        showBanner(verdict);
    }
});

// React instantly if background script updates storage after page load
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes[window.location.hostname]) {
        const verdict = changes[window.location.hostname].newValue;
        if (verdict && (verdict.tier === "BLOCK" || verdict.tier === "WARN")) {
            showBanner(verdict);
        }
    }
});