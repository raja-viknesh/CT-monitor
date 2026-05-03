(function (global) {
    const BRANDS = [
        "google", "microsoft", "apple", "amazon", "paypal", "github", "netflix", "whatsapp",
        "instagram", "facebook", "linkedin", "dropbox", "adobe", "x", "openai", "binance"
    ];

    const SUSPICIOUS_TLDS = new Set([
        "zip", "mov", "xyz", "top", "click", "loan", "gq", "tk", "cf", "ml", "work", "rest"
    ]);

    const RISKY_KEYWORDS = [
        "login", "secure", "verify", "update", "account", "signin", "wallet", "auth", "support"
    ];

    const TRUSTED_DOMAINS = new Set([
        "google.com", "microsoft.com", "apple.com", "amazon.com", "github.com", "mozilla.org",
        "wikipedia.org", "cloudflare.com", "lenovo.com", "devpost.com"
    ]);

    function clamp01(v) {
        if (v < 0) return 0;
        if (v > 1) return 1;
        return v;
    }

    function entropy(text) {
        if (!text || text.length <= 1) return 0;
        const freq = {};
        for (const c of text.toLowerCase()) {
            freq[c] = (freq[c] || 0) + 1;
        }
        let ent = 0;
        for (const key of Object.keys(freq)) {
            const p = freq[key] / text.length;
            ent -= p * Math.log2(p);
        }
        const maxEnt = Math.log2(Math.min(64, Object.keys(freq).length || 1));
        return maxEnt > 0 ? ent / maxEnt : 0;
    }

    function levenshtein(a, b) {
        const n = a.length;
        const m = b.length;
        if (n === 0) return m;
        if (m === 0) return n;

        const dp = Array.from({ length: n + 1 }, (_, i) => {
            const row = new Array(m + 1).fill(0);
            row[0] = i;
            return row;
        });
        for (let j = 0; j <= m; j++) dp[0][j] = j;

        for (let i = 1; i <= n; i++) {
            for (let j = 1; j <= m; j++) {
                const cost = a[i - 1] === b[j - 1] ? 0 : 1;
                dp[i][j] = Math.min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost
                );
            }
        }
        return dp[n][m];
    }

    function bestBrandMatch(label) {
        let best = { brand: null, score: 0, distance: 999 };
        for (const brand of BRANDS) {
            const dist = levenshtein(label, brand);
            const ratio = 1 - dist / Math.max(label.length, brand.length, 1);
            if (ratio > best.score) {
                best = { brand, score: ratio, distance: dist };
            }
        }
        return best;
    }

    function safeURL(hostOrUrl) {
        try {
            if (hostOrUrl.includes("://")) {
                return new URL(hostOrUrl).hostname.toLowerCase();
            }
            return hostOrUrl.toLowerCase();
        } catch {
            return hostOrUrl.toLowerCase();
        }
    }

    function toETLD1(host) {
        const parts = host.split(".").filter(Boolean);
        if (parts.length <= 2) return host;
        return parts.slice(-2).join(".");
    }

    function labelPart(host) {
        return host.split(".")[0] || host;
    }

    function tldPart(host) {
        const parts = host.split(".").filter(Boolean);
        return parts.length ? parts[parts.length - 1] : "";
    }

    function detector(name, score, confidence, evidence) {
        return {
            detector_name: name,
            score: clamp01(score),
            confidence: clamp01(confidence),
            evidence: evidence || {},
            latency_ms: 0.1,
        };
    }

    function structuralRisk(host) {
        const parts = host.split(".").filter(Boolean);
        const label = parts[0] || "";
        const subDepth = Math.max(0, parts.length - 2);
        const hyphens = (label.match(/-/g) || []).length;
        const digits = (label.match(/[0-9]/g) || []).length;
        const ratioDigits = label.length ? digits / label.length : 0;

        let score = 0;
        score += Math.min(0.35, subDepth * 0.08);
        score += Math.min(0.25, hyphens * 0.06);
        score += Math.min(0.2, ratioDigits * 0.6);
        if (label.length > 18) score += 0.12;

        return {
            score: clamp01(score),
            evidence: {
                subdomain_depth: subDepth,
                hyphens,
                digits,
                digit_ratio: Number(ratioDigits.toFixed(3)),
                label_length: label.length,
            },
        };
    }

    function analyzeDomain(domainInput) {
        const started = performance && performance.now ? performance.now() : Date.now();
        const host = safeURL(domainInput);
        const etld1 = toETLD1(host);
        const label = labelPart(host).replace(/[^a-z0-9-]/gi, "").toLowerCase();
        const tld = tldPart(host);
        const unicodeDomain = host;
        const trusted = TRUSTED_DOMAINS.has(etld1);

        const detectors = [];

        const match = bestBrandMatch(label);
        const brandScore = match.brand ? clamp01(match.score > 0.7 ? 0.7 + ((match.score - 0.7) * 1.0) : match.score * 0.5) : 0;
        detectors.push(detector("LevenshteinDetector", brandScore, 0.8, {
            matched_brand: match.brand,
            ratio: Number(match.score.toFixed(3)),
            distance: match.distance,
            domain: etld1,
        }));

        const idnLike = host.includes("xn--") || /[\u0400-\u04FF\u0370-\u03FF]/.test(host);
        detectors.push(detector("HomographDetector", idnLike ? 1 : 0, 0.95, {
            unicode_domain: unicodeDomain,
            has_confusable: idnLike,
        }));

        const keywordHits = RISKY_KEYWORDS.filter((k) => host.includes(k));
        const tldKeywordScore = keywordHits.length && SUSPICIOUS_TLDS.has(tld)
            ? 0.85
            : keywordHits.length
                ? 0.45
                : SUSPICIOUS_TLDS.has(tld)
                    ? 0.35
                    : 0;
        detectors.push(detector("TLDKeywordDetector", tldKeywordScore, 0.85, {
            keyword_hits: keywordHits,
            tld,
            suspicious_tld: SUSPICIOUS_TLDS.has(tld),
        }));

        const sanProxy = host.split("-").length + host.split(".").length;
        const sanScore = clamp01((sanProxy - 5) / 15);
        detectors.push(detector("SANAnomalyDetector", sanScore, 0.6, {
            san_proxy_count: sanProxy,
        }));

        const ageScore = (keywordHits.length > 0 || match.score > 0.75) ? 0.55 : 0.2;
        detectors.push(detector("DomainAgeDetector", ageScore, 0.55, {
            source: "extension-local-heuristic",
            note: "WHOIS unavailable in extension-only mode",
        }));

        const ent = entropy(label);
        detectors.push(detector("NgramLMDetector", clamp01((ent - 0.45) / 0.5), 0.65, {
            entropy: Number(ent.toFixed(3)),
            mode: "local-sim",
        }));

        const structure = structuralRisk(host);
        detectors.push(detector("StructureDetector", structure.score, 0.7, structure.evidence));

        const weighted = detectors.map((d) => d.score * d.confidence);
        const confSum = detectors.reduce((acc, d) => acc + d.confidence, 0) || 1;
        let risk = clamp01(weighted.reduce((a, b) => a + b, 0) / confSum);

        if (trusted && risk < 0.55) {
            risk *= 0.25;
        }

        if (!trusted && (keywordHits.length > 0 || structure.score > 0.4)) {
            risk = clamp01(risk + 0.08);
        }

        let tier = "SAFE";
        if (risk >= 0.85) tier = "BLOCK";
        else if (risk >= 0.6) tier = "WARN";
        else if (risk >= 0.35) tier = "WATCH";

        const sorted = detectors.slice().sort((a, b) => b.score - a.score);
        const reasoning = sorted.slice(0, 3).map((d) => {
            return `${d.detector_name} score ${(d.score * 100).toFixed(1)}%`; 
        });

        const ended = performance && performance.now ? performance.now() : Date.now();
        const latency = Math.max(0.1, ended - started);

        return {
            domain: host,
            risk_score: Number(risk.toFixed(4)),
            tier,
            confidence_lower: Number(clamp01(risk - 0.15).toFixed(4)),
            confidence_upper: Number(clamp01(risk + 0.15).toFixed(4)),
            detector_results: detectors,
            combined_belief: Number(clamp01(risk * 0.9).toFixed(4)),
            combined_plausibility: Number(clamp01(risk + 0.1).toFixed(4)),
            latency_ms: Number(latency.toFixed(3)),
            ts: new Date().toISOString(),
            analysis: {
                summary: {
                    belief_threat: Number(clamp01(risk * 0.9).toFixed(4)),
                    plausibility_threat: Number(clamp01(risk + 0.1).toFixed(4)),
                    uncertainty: Number(clamp01(1 - risk).toFixed(4)),
                },
                reasoning,
                signals: sorted.slice(0, 4),
                meta: {
                    trusted_domain: trusted,
                    etld_plus_one: etld1,
                },
            },
        };
    }

    global.CTLocalEngine = {
        analyzeDomain,
    };
})(typeof self !== "undefined" ? self : window);
