"""
src/tailoring/ats_validator.py

ATS Validator — checks a resume (LaTeX or plain text) for patterns
that cause Applicant Tracking System failures. Runs entirely locally.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ATSIssue:
    severity: str            # critical | warning | info
    code: str                # machine-readable code
    message: str             # human-readable explanation
    suggestion: str          # how to fix it


@dataclass
class ATSReport:
    issues: list[ATSIssue] = field(default_factory=list)
    keyword_matches: list[str] = field(default_factory=list)
    keyword_missing: list[str] = field(default_factory=list)
    pass_probability: int = 100   # 0-100%, deducted per issue severity

    @property
    def passed(self) -> bool:
        return not any(i.severity == "critical" for i in self.issues)

    def summary(self) -> str:
        critical = sum(1 for i in self.issues if i.severity == "critical")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        return (
            f"ATS: {self.pass_probability}% pass probability | "
            f"{critical} critical, {warnings} warnings | "
            f"{len(self.keyword_matches)}/{len(self.keyword_matches)+len(self.keyword_missing)} keywords matched"
        )


class ATSValidator:
    """
    Validates resume content against common ATS failure patterns.
    Checks both LaTeX formatting patterns and plain-text content.
    """

    # Deductions per severity
    _DEDUCTIONS = {"critical": 25, "warning": 10, "info": 2}

    def validate(
        self,
        resume_text: str,
        required_keywords: list[str] | None = None,
        is_latex: bool = False,
    ) -> ATSReport:
        report = ATSReport()
        plain = _latex_to_plain(resume_text) if is_latex else resume_text

        # ── Format checks ─────────────────────────────────────────────────────
        if is_latex:
            self._check_latex_format(resume_text, report)
        self._check_plain_format(plain, report)

        # ── Keyword checks ────────────────────────────────────────────────────
        if required_keywords:
            self._check_keywords(plain, required_keywords, report)

        # ── Content quality checks ────────────────────────────────────────────
        self._check_content_quality(plain, report)

        # ── Calculate pass probability ────────────────────────────────────────
        deductions = sum(
            self._DEDUCTIONS.get(i.severity, 0) for i in report.issues
        )
        report.pass_probability = max(0, 100 - deductions)

        return report

    # ─── Check groups ─────────────────────────────────────────────────────────

    def _check_latex_format(self, latex: str, report: ATSReport) -> None:
        # LaTeX tables are problematic for some ATS
        if re.search(r"\\begin\{tabular\}.*\\end\{tabular\}", latex, re.DOTALL):
            if latex.count(r"\begin{tabular}") > 3:
                report.issues.append(ATSIssue(
                    severity="warning",
                    code="LATEX_HEAVY_TABLES",
                    message="Heavy use of LaTeX tabular environments detected",
                    suggestion="ATS parses tabular text poorly. Ensure key info appears in resumeItem too.",
                ))
        # Multi-column layout
        if "multicol" in latex or "twocolumn" in latex:
            report.issues.append(ATSIssue(
                severity="critical",
                code="MULTI_COLUMN",
                message="Multi-column layout detected",
                suggestion="Most ATS read left-to-right linearly. Use single-column layout.",
            ))

    def _check_plain_format(self, plain: str, report: ATSReport) -> None:
        # Check for special characters that may not parse
        if "□" in plain or "■" in plain or "▪" in plain:
            report.issues.append(ATSIssue(
                severity="warning",
                code="SPECIAL_BULLETS",
                message="Non-standard bullet characters found",
                suggestion="Use standard hyphens or bullets (•, -, *) for ATS compatibility.",
            ))
        # Very short resume
        if len(plain.split()) < 200:
            report.issues.append(ATSIssue(
                severity="warning",
                code="TOO_SHORT",
                message=f"Resume is very short ({len(plain.split())} words)",
                suggestion="ATS systems may penalise sparse resumes. Aim for 400-700 words.",
            ))
        # Very long resume
        if len(plain.split()) > 1200:
            report.issues.append(ATSIssue(
                severity="warning",
                code="TOO_LONG",
                message=f"Resume is very long ({len(plain.split())} words)",
                suggestion="Keep to 1 page for < 5yr exp, 2 pages max for senior roles.",
            ))

    def _check_keywords(
        self, plain: str, keywords: list[str], report: ATSReport
    ) -> None:
        plain_lower = plain.lower()
        for kw in keywords:
            if kw.lower() in plain_lower:
                report.keyword_matches.append(kw)
            else:
                report.keyword_missing.append(kw)
                report.issues.append(ATSIssue(
                    severity="warning",
                    code=f"MISSING_KEYWORD",
                    message=f"Required keyword missing: '{kw}'",
                    suggestion=(
                        f"Include '{kw}' naturally if you have this skill/experience. "
                        "Do not add it if you don't."
                    ),
                ))

    def _check_content_quality(self, plain: str, report: ATSReport) -> None:
        # No contact info
        if not re.search(r"@\w+\.\w+", plain):
            report.issues.append(ATSIssue(
                severity="critical",
                code="NO_EMAIL",
                message="No email address detected",
                suggestion="Ensure your email is in plain text (not an image or hyperlink only).",
            ))
        # No dates
        if not re.search(r"\b(20\d{2}|19\d{2})\b", plain):
            report.issues.append(ATSIssue(
                severity="warning",
                code="NO_DATES",
                message="No years detected in resume",
                suggestion="Include years for all positions and education.",
            ))
        # Keyword stuffing
        words = plain.lower().split()
        word_freq: dict[str, int] = {}
        for w in words:
            if len(w) > 4:
                word_freq[w] = word_freq.get(w, 0) + 1
        stuffed = [w for w, c in word_freq.items() if c > 8]
        if stuffed:
            report.issues.append(ATSIssue(
                severity="warning",
                code="KEYWORD_STUFFING",
                message=f"Potential keyword stuffing: {', '.join(stuffed[:3])}",
                suggestion="Reduce repetition. ATS may flag over-optimised resumes.",
            ))


def _latex_to_plain(latex: str) -> str:
    text = re.sub(r"\\resumeItem\{([^}]*)\}", r"• \1", latex)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = re.sub(r"[{}%]", "", text)
    return re.sub(r"\s+", " ", text).strip()