const HOSTNAME = window.location.hostname;
const STATE_KEY = HOSTNAME;
const ROOT_ID = "ctmonitor-root";
const BANNER_ID = "ctmonitor-banner";
const PILL_ID = "ctmonitor-state-pill";

function getMountNode() {
    return document.body || document.documentElement;
}

function ensureRoot() {
    let root = document.getElementById(ROOT_ID);
    if (root) return root;

    root = document.createElement("div");
    root.id = ROOT_ID;
    root.style.position = "fixed";
    root.style.inset = "0";
    root.style.zIndex = "2147483647";
    root.style.pointerEvents = "none";
    getMountNode().appendChild(root);
    return root;
}

function hideElement(id) {
    const element = document.getElementById(id);
    if (element) element.remove();
}

function showAnalyzingScreen() {
    hideElement(BANNER_ID);
    const root = ensureRoot();

    let screen = document.getElementById("ctmonitor-analyzing-screen");
    if (!screen) {
        screen = document.createElement("div");
        screen.id = "ctmonitor-analyzing-screen";
        screen.style.position = "absolute";
        screen.style.inset = "0";
        screen.style.display = "flex";
        screen.style.alignItems = "center";
        screen.style.justifyContent = "center";
        screen.style.background = "rgba(10, 14, 20, 0.55)";
        screen.style.backdropFilter = "blur(8px)";
        screen.style.pointerEvents = "none";

        const card = document.createElement("div");
        card.style.pointerEvents = "auto";
        card.style.minWidth = "280px";
        card.style.maxWidth = "420px";
        card.style.margin = "24px";
        card.style.padding = "20px 22px";
        card.style.borderRadius = "16px";
        card.style.background = "#111827";
        card.style.color = "#f9fafb";
        card.style.boxShadow = "0 16px 40px rgba(0, 0, 0, 0.35)";
        card.style.fontFamily = "system-ui, sans-serif";
        card.style.textAlign = "left";

        const spinner = document.createElement("div");
        spinner.style.width = "14px";
        spinner.style.height = "14px";
        spinner.style.borderRadius = "999px";
        spinner.style.border = "2px solid rgba(148, 163, 184, 0.35)";
        spinner.style.borderTopColor = "#60a5fa";
        spinner.style.animation = "ctmonitor-spin 0.8s linear infinite";
        spinner.style.marginBottom = "14px";

        const title = document.createElement("div");
        title.style.fontSize = "18px";
        title.style.fontWeight = "700";
        title.style.marginBottom = "8px";
        title.textContent = "CTMonitor is analyzing this page";

        const body = document.createElement("div");
        body.style.fontSize = "13px";
        body.style.lineHeight = "1.5";
        body.style.color = "#cbd5e1";
        body.textContent = "Local heuristics are running now. A verdict will appear as soon as the engine responds.";

        const style = document.createElement("style");
        style.textContent = "@keyframes ctmonitor-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }";

        card.appendChild(spinner);
        card.appendChild(title);
        card.appendChild(body);
        screen.appendChild(card);
        screen.appendChild(style);
        root.appendChild(screen);
    }

    screen.style.display = "flex";

    let pill = document.getElementById(PILL_ID);
    if (!pill) {
        pill = document.createElement("div");
        pill.id = PILL_ID;
        pill.style.position = "fixed";
        pill.style.bottom = "20px";
        pill.style.right = "20px";
        pill.style.padding = "8px 15px";
        pill.style.borderRadius = "20px";
        pill.style.fontFamily = "system-ui, sans-serif";
        pill.style.fontSize = "13px";
        pill.style.fontWeight = "bold";
        pill.style.zIndex = "2147483646";
        pill.style.boxShadow = "0 4px 6px rgba(0,0,0,0.2)";
        pill.style.transition = "all 0.3s ease";
        pill.style.pointerEvents = "none";
        root.appendChild(pill);
    }

    pill.style.display = "block";
    pill.style.opacity = "1";
    pill.style.backgroundColor = "#333";
    pill.style.color = "white";
    pill.textContent = "CTMonitor: analyzing...";
}

function showBanner(verdict) {
    hideElement("ctmonitor-analyzing-screen");

    let banner = document.getElementById(BANNER_ID);
    if (!banner) {
        banner = document.createElement("div");
        banner.id = BANNER_ID;
        banner.style.position = "fixed";
        banner.style.top = "0";
        banner.style.left = "0";
        banner.style.width = "100%";
        banner.style.color = "white";
        banner.style.textAlign = "center";
        banner.style.padding = "12px 16px";
        banner.style.zIndex = "2147483647";
        banner.style.fontFamily = "system-ui, sans-serif";
        banner.style.fontWeight = "700";
        banner.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
        banner.style.pointerEvents = "auto";
        banner.style.cursor = "pointer";

        const message = document.createElement("span");
        message.id = "ctmonitor-banner-message";
        banner.appendChild(message);

        const actions = document.createElement("span");
        actions.id = "ctmonitor-banner-actions";
        actions.style.marginLeft = "12px";
        banner.appendChild(actions);

        const dismiss = document.createElement("button");
        dismiss.id = "ctmonitor-dismiss";
        dismiss.type = "button";
        dismiss.textContent = "Dismiss";
        dismiss.style.cursor = "pointer";
        dismiss.style.marginLeft = "16px";
        dismiss.style.border = "0";
        dismiss.style.borderRadius = "999px";
        dismiss.style.padding = "6px 12px";
        dismiss.style.fontWeight = "700";
        dismiss.style.background = "rgba(255, 255, 255, 0.18)";
        dismiss.style.color = "white";
        dismiss.addEventListener("click", () => banner.remove());

        const viewReport = document.createElement("button");
        viewReport.type = "button";
        viewReport.textContent = "View report";
        viewReport.style.cursor = "pointer";
        viewReport.style.marginLeft = "8px";
        viewReport.style.border = "0";
        viewReport.style.borderRadius = "999px";
        viewReport.style.padding = "6px 12px";
        viewReport.style.fontWeight = "700";
        viewReport.style.background = "rgba(255, 255, 255, 0.18)";
        viewReport.style.color = "white";
        viewReport.addEventListener("click", () => {
            chrome.runtime.sendMessage({type: "open-report", domain: HOSTNAME});
        });

        const reanalyze = document.createElement("button");
        reanalyze.type = "button";
        reanalyze.textContent = "Reanalyze";
        reanalyze.style.cursor = "pointer";
        reanalyze.style.marginLeft = "8px";
        reanalyze.style.border = "0";
        reanalyze.style.borderRadius = "999px";
        reanalyze.style.padding = "6px 12px";
        reanalyze.style.fontWeight = "700";
        reanalyze.style.background = "rgba(255, 255, 255, 0.18)";
        reanalyze.style.color = "white";
        reanalyze.addEventListener("click", () => {
            chrome.runtime.sendMessage({type: "reanalyze-domain", domain: HOSTNAME}, () => {});
        });

        const actionsNode = banner.querySelector("#ctmonitor-banner-actions");
        actionsNode.appendChild(viewReport);
        actionsNode.appendChild(reanalyze);
        actionsNode.appendChild(dismiss);

        banner.addEventListener("click", (event) => {
            if (event.target && event.target.tagName === "BUTTON") return;
            chrome.runtime.sendMessage({type: "open-report", domain: HOSTNAME});
        });

        ensureRoot().appendChild(banner);
    }

    banner.style.backgroundColor = verdict.tier === "BLOCK" ? "#E24B4A" : "#EF9F27";
    const message = document.getElementById("ctmonitor-banner-message");
    if (message) {
        message.textContent = `CTMonitor flagged this page. Risk score: ${(verdict.risk_score * 100).toFixed(1)}%.`;
    }

    const pill = document.getElementById(PILL_ID);
    if (pill) pill.style.display = "none";
}

function updateVisuals(data) {
    if (!data) return;

    if (data.status === "ANALYZING") {
        showAnalyzingScreen();
        return;
    }

    hideElement("ctmonitor-analyzing-screen");

    const root = ensureRoot();
    let pill = document.getElementById(PILL_ID);
    if (!pill) {
        pill = document.createElement("div");
        pill.id = PILL_ID;
        pill.style.position = "fixed";
        pill.style.bottom = "20px";
        pill.style.right = "20px";
        pill.style.padding = "8px 15px";
        pill.style.borderRadius = "20px";
        pill.style.fontFamily = "system-ui, sans-serif";
        pill.style.fontSize = "13px";
        pill.style.fontWeight = "bold";
        pill.style.zIndex = "2147483646";
        pill.style.boxShadow = "0 4px 6px rgba(0,0,0,0.2)";
        pill.style.transition = "all 0.3s ease";
        pill.style.pointerEvents = "none";
        root.appendChild(pill);
    }

    if (data.status === "ERROR") {
        pill.style.display = "block";
        pill.style.opacity = "1";
        pill.style.backgroundColor = "#E24B4A";
        pill.style.color = "white";
        pill.textContent = "CTMonitor: offline";
        return;
    }

    if (data.tier === "SAFE" || data.tier === "WATCH") {
        pill.style.display = "block";
        pill.style.opacity = "1";
        pill.style.backgroundColor = "#4aff8b";
        pill.style.color = "#000";
        pill.textContent = `CTMonitor: ${data.tier} (${(data.risk_score * 100).toFixed(1)}%)`;
        setTimeout(() => {
            pill.style.opacity = "0";
            setTimeout(() => { pill.style.display = "none"; }, 300);
        }, 3000);
        return;
    }

    if (data.tier) {
        showBanner(data);
    }
}

updateVisuals({ status: "ANALYZING" });

chrome.storage.local.get(STATE_KEY, (items) => {
    if (items && items[STATE_KEY]) {
        updateVisuals(items[STATE_KEY]);
    }
});

chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === "local" && changes[STATE_KEY]) {
        updateVisuals(changes[STATE_KEY].newValue);
    }
});
