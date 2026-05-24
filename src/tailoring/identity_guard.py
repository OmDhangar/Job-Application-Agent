"""
src/tailoring/identity_guard.py

Prevents the tailoring engine from fabricating experience.
Runs locally after every Gemini call — zero API cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from src.schemas.candidate import IdentityProfile


class IdentityGuard:
    def __init__(self, identity: IdentityProfile) -> None:
        self.identity = identity

    def audit(
        self,
        original: str,
        tailored: str,
        job_skills: list[str],
    ) -> dict:
        issues: list[str] = []
        original_lower = original.lower()
        tailored_lower = tailored.lower()

        # 1. Fabricated skills
        for skill in job_skills:
            if skill.lower() not in original_lower and skill.lower() in tailored_lower:
                issues.append(f"FABRICATED_SKILL: '{skill}' added but not in original")

        # 2. Fabricated companies
        for co in self.identity.companies_worked:
            # original companies should still be there
            if co.lower() not in tailored_lower:
                issues.append(f"IDENTITY_ERASED: company '{co}' was removed")

        # 3. Keyword stuffing
        for skill in job_skills:
            count = tailored_lower.count(skill.lower())
            if count > 5:
                issues.append(f"KEYWORD_STUFFING: '{skill}' appears {count}x")

        # 4. Voice marker preservation
        for marker in self.identity.voice_markers[:2]:
            if marker and len(marker) > 10 and marker.lower() not in tailored_lower:
                issues.append(f"IDENTITY_ERASED: voice marker '{marker[:30]}' removed")

        fabrication_risk = sum(1 for i in issues if "FABRICATED" in i)
        stuffing_risk = sum(1 for i in issues if "STUFFING" in i)

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "fabrication_risk": fabrication_risk,
            "stuffing_risk": stuffing_risk,
            "severity": "high" if fabrication_risk > 0 else ("medium" if stuffing_risk > 0 else "low"),
        }