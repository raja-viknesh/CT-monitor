chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    let url = new URL(tabs[0].url);
    let domain = url.hostname;
    
    document.getElementById("domain-name").textContent = domain;
    
    // Check background.js API response cache
    chrome.storage.local.get([tabs[0].id.toString()], (result) => {
        let verdict = result[tabs[0].id.toString()];
        if (verdict) {
            document.getElementById("score-display").textContent = (verdict.risk_score * 100).toFixed(1) + "% Risk";
            document.getElementById("tier-display").textContent = "Tier: " + verdict.tier;
            document.getElementById("tier-display").className = verdict.tier;
            document.getElementById("score-display").className = "score " + verdict.tier;
        } else {
            document.getElementById("score-display").textContent = "Unscanned";
            document.getElementById("tier-display").textContent = "N/A";
        }
    });
});