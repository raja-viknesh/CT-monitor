"""Dempster-Shafer Quorum Combiner."""

class DempsterShafer:
    @staticmethod
    def mass_function(score: float, confidence: float) -> dict:
        """Calculate masses for threat, safe, and ignorance (theta)."""
        theta = 1.0 - confidence
        threat = score * confidence
        safe = (1.0 - score) * confidence
        return {"threat": threat, "safe": safe, "theta": theta}

    @staticmethod
    def combine(m1: dict, m2: dict) -> dict:
        """Combine two mass functions using Dempster's rule."""
        conflict = m1["threat"] * m2["safe"] + m1["safe"] * m2["threat"]
        k = 1.0 - conflict
        if k < 0.01: # High conflict fallback
            return {
                "threat": (m1["threat"] + m2["threat"]) / 2,
                "safe": (m1["safe"] + m2["safe"]) / 2,
                "theta": (m1["theta"] + m2["theta"]) / 2
            }
            
        threat = (m1["threat"] * m2["threat"] + m1["threat"] * m2["theta"] + m1["theta"] * m2["threat"]) / k
        safe = (m1["safe"] * m2["safe"] + m1["safe"] * m2["theta"] + m1["theta"] * m2["safe"]) / k
        theta = (m1["theta"] * m2["theta"]) / k
        return {"threat": threat, "safe": safe, "theta": theta}
