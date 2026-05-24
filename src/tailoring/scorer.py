# ─── Scorer ───────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
from dataclasses import dataclass as _dc

from src.enrichment.jd_analyzer import JDAnalysis
from src.schemas.candidate import IdentityProfile
 
@_dc
class ResumeScores:
    ats_score: float
    authenticity_score: float
    recruiter_readability: float
    technical_credibility: float
    interview_probability: float
    composite: float
 
 
class ResumeScorer:
    def score(
        self,
        tailored: str,
        jd: JDAnalysis,
        identity: IdentityProfile,
        critique: str,
    ) -> ResumeScores:
        # Strip LaTeX for text-based scoring
        plain = _strip_latex(tailored)
 
        ats          = self._ats(plain, jd)
        auth         = self._authenticity(plain, identity)
        readability  = self._readability(plain)
        credibility  = self._credibility(plain)
        critic_score = self._critic_numeric(critique)
 
        composite = (
            ats         * 0.30
            + auth      * 0.25
            + readability * 0.20
            + credibility * 0.15
            + critic_score * 0.10
        )
        return ResumeScores(
            ats_score=round(ats, 1),
            authenticity_score=round(auth, 1),
            recruiter_readability=round(readability, 1),
            technical_credibility=round(credibility, 1),
            interview_probability=round(composite * 0.85, 1),
            composite=round(composite, 1),
        )
 
    def _ats(self, plain: str, jd: JDAnalysis) -> float:
        if not jd.ats_keywords:
            return 65.0
        lower = plain.lower()
        matched = sum(1 for kw in jd.ats_keywords if kw.lower() in lower)
        return min(100.0, (matched / len(jd.ats_keywords)) * 100)
 
    def _authenticity(self, plain: str, identity: IdentityProfile) -> float:
        score = 100.0
        lower = plain.lower()
        for co in identity.companies_worked:
            if co.lower() not in lower:
                score -= 15
        return max(0.0, score)
 
    def _readability(self, plain: str) -> float:
        score = 65.0
        bullets = [l for l in plain.split("\n") if l.strip().startswith("•")]
        score += min(20.0, len(bullets) * 1.5)
        long_bullets = [b for b in bullets if len(b) > 200]
        score -= len(long_bullets) * 5
        return min(100.0, max(0.0, score))
 
    def _credibility(self, plain: str) -> float:
        score = 50.0
        numbers = re.findall(r"\d+\s*[%xX×]|\d+\s*(ms|TB|GB|K|M|hrs?)", plain)
        score += min(30.0, len(numbers) * 5)
        verbs = ["built", "scaled", "optimized", "led", "designed", "reduced",
                 "improved", "deployed", "architected", "automated"]
        score += sum(3 for v in verbs if v in plain.lower())
        return min(100.0, score)
 
    def _critic_numeric(self, critique: str) -> float:
        m = re.search(r"(\d+)\s*/\s*10", critique)
        return float(m.group(1)) * 10 if m else 60.0
 
 
def _strip_latex(text: str) -> str:
    """Lightweight LaTeX → plain for scoring."""
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = re.sub(r"[{}%]", "", text)
    return re.sub(r"\s+", " ", text).strip()