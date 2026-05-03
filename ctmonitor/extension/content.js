// Content script for CTMonitor
// Injects a warning banner if the page is blocked or warned

chrome.storage.local.get(null, (items) => {
    const verdict = items[window.location.hostname];
    if (verdict && verdict.tier === "BLOCK") {
        const banner = document.createElement("div");
        banner.style.position = "fixed";
        banner.style.top = "0";
        banner.style.left = "0";
        banner.style.width = "100%";
        banner.style.backgroundColor = "#E24B4A";
        banner.style.color = "white";
        banner.style.textAlign = "center";
        banner.style.padding = "10px";
        banner.style.zIndex = "999999999";
        banner.style.fontFamily = "sans-serif";
        banner.style.fontWeight = "bold";
        banner.innerHTML = `⚠️ CTMonitor blocked this page. Risk Score: ${(verdict.risk_score * 100).toFixed(1)}%. <span style="cursor:pointer; text-decoration:underline;" id="ctmonitor-dismiss">Dismiss</span>`;
        
        document.body.prepend(banner);
        
        document.getElementById("ctmonitor-dismiss").addEventListener("click", () => {
            banner.remove();
        });
    }
});