const params = new URLSearchParams(window.location.search);
const tabId = Number(params.get("tabId") || "0");
const domain = (params.get("domain") || "").trim();

document.getElementById("domain").textContent = domain || "unknown";

function setStatus(text) {
    document.getElementById("status").textContent = text;
}

document.getElementById("continue-btn").addEventListener("click", async () => {
    const response = await chrome.runtime.sendMessage({
        type: "continue-block-navigation",
        tabId,
    });
    if (response?.ok) {
        setStatus("Continuing to original page...");
    } else {
        setStatus(response?.error || "Unable to continue navigation.");
    }
});

document.getElementById("back-btn").addEventListener("click", async () => {
    await chrome.runtime.sendMessage({ type: "dismiss-block-navigation", tabId });
    window.location.href = "about:blank";
});

document.getElementById("report-btn").addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "open-report", domain });
});
