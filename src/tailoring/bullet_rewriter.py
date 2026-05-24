"""
src/tailoring/bullet_rewriter.py

Bullet Rewriter — improves individual resume bullets locally.
Applies verb strengthening, quantification nudges, and structure fixes
WITHOUT an LLM call for basic rewrites. LLM is invoked only for
complex semantic improvements.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ─── Weak verb replacement map ────────────────────────────────────────────────
# Maps weak/vague verbs → stronger domain-appropriate alternatives.
_VERB_UPGRADES: dict[str, str] = {
    "worked on":       "developed",
    "helped with":     "contributed to",
    "was responsible": "owned",
    "did":             "executed",
    "made":            "built",
    "fixed":           "resolved",
    "changed":         "refactored",
    "updated":         "enhanced",
    "wrote":           "authored",
    "used":            "leveraged",
    "worked with":     "collaborated on",
    "involved in":     "drove",
    "part of":         "contributed to",
    "assisted":        "supported",
    "looked at":       "analysed",
}

# Role-specific strong openers
_DOMAIN_VERBS: dict[str, list[str]] = {
    "backend":   ["Architected", "Designed", "Built", "Optimised", "Scaled", "Deployed", "Migrated"],
    "ml":        ["Trained", "Fine-tuned", "Deployed", "Benchmarked", "Improved", "Developed"],
    "frontend":  ["Implemented", "Redesigned", "Optimised", "Built", "Reduced"],
    "devops":    ["Automated", "Containerised", "Provisioned", "Migrated", "Reduced"],
    "data":      ["Modelled", "Ingested", "Orchestrated", "Reduced", "Built"],
    "research":  ["Published", "Proposed", "Evaluated", "Demonstrated", "Developed"],
    "fullstack": ["Built", "Designed", "Implemented", "Led", "Delivered"],
}


@dataclass
class BulletAnalysis:
    original: str
    has_metric: bool        # contains a number / %
    has_action_verb: bool   # starts with a strong verb
    has_outcome: bool       # mentions impact / result
    word_count: int
    issues: list[str]
    score: int              # 0-100


@dataclass
class RewrittenBullet:
    original: str
    rewritten: str
    changes_made: list[str]
    confidence: float       # 0-1; low = needs LLM, high = rule-based is fine


class BulletRewriter:
    """
    Local rule-based bullet rewriter.
    For complex semantic rewrites, returns low confidence → caller uses LLM.
    """

    def analyse(self, bullet: str) -> BulletAnalysis:
        clean = bullet.lstrip("•-* ").strip()
        has_metric    = bool(re.search(r"\d+\s*[%x×]|\d+\s*(ms|TB|GB|MB|K|M|hrs?|days?)", clean))
        has_verb      = bool(re.match(r"^[A-Z][a-z]+ed|^[A-Z][a-z]+ed\b", clean))
        has_outcome   = any(
            kw in clean.lower() for kw in
            ["result", "impact", "reduc", "increas", "improv", "enabl", "allow", "lead to"]
        )
        issues = []
        if not has_metric:
            issues.append("no_metric")
        if not has_verb:
            issues.append("weak_verb")
        if not has_outcome:
            issues.append("no_outcome")
        if len(clean.split()) < 8:
            issues.append("too_short")
        if len(clean.split()) > 35:
            issues.append("too_long")
        score = 100 - (len(issues) * 20)
        return BulletAnalysis(
            original=bullet, has_metric=has_metric, has_action_verb=has_verb,
            has_outcome=has_outcome, word_count=len(clean.split()),
            issues=issues, score=max(0, score),
        )

    def rewrite(self, bullet: str, domain: str = "backend") -> RewrittenBullet:
        analysis = self.analyse(bullet)
        clean = bullet.lstrip("•-* ").strip()
        changes: list[str] = []

        # 1. Upgrade weak verbs
        rewritten = self._upgrade_verb(clean)
        if rewritten != clean:
            changes.append("upgraded_verb")
        clean = rewritten

        # 2. Capitalise first word if needed
        if clean and not clean[0].isupper():
            clean = clean[0].upper() + clean[1:]
            changes.append("capitalised")

        # 3. Remove trailing period (ATS convention — keep consistent)
        if clean.endswith("."):
            clean = clean[:-1]
            changes.append("removed_trailing_period")

        # Confidence: high if only surface fixes, low if semantic rewrite needed
        semantic_issues = {"no_metric", "no_outcome", "weak_verb"} & set(analysis.issues)
        confidence = 0.9 if not semantic_issues else max(0.3, 1.0 - len(semantic_issues) * 0.25)

        return RewrittenBullet(
            original=bullet, rewritten="• " + clean,
            changes_made=changes, confidence=confidence,
        )

    def rewrite_batch(
        self, bullets: list[str], domain: str = "backend"
    ) -> list[RewrittenBullet]:
        return [self.rewrite(b, domain) for b in bullets]

    def extract_bullets_from_latex(self, latex: str) -> list[str]:
        """Pull \\resumeItem{...} content from LaTeX source."""
        return re.findall(r"\\resumeItem\{([^}]+)\}", latex)

    def replace_bullets_in_latex(
        self, latex: str, replacements: dict[str, str]
    ) -> str:
        """Replace \\resumeItem content. replacements = {original_text: new_text}"""
        for orig, new in replacements.items():
            escaped = re.escape(orig)
            latex = re.sub(
                r"(\\resumeItem\{)" + escaped + r"(\})",
                r"\g<1>" + new + r"\g<2>",
                latex,
            )
        return latex

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _upgrade_verb(self, text: str) -> str:
        lower = text.lower()
        for weak, strong in _VERB_UPGRADES.items():
            if lower.startswith(weak):
                remainder = text[len(weak):]
                return strong.capitalize() + remainder
        return text