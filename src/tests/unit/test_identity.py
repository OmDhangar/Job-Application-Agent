"""
tests/unit/test_identity_guard.py
tests/unit/test_strategy.py
tests/unit/test_scorer.py
"""
import pytest
from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME, SAMPLE_JD_BACKEND, SAMPLE_IDENTITY_JSON
from src.tailoring.identity_guard import IdentityGuard
from src.enrichment.jd_analyzer import JDAnalysis
from src.schemas.candidate import IdentityProfile


# ─── IdentityGuard ────────────────────────────────────────────────────────────

def make_identity(**kwargs) -> IdentityProfile:
    base = SAMPLE_IDENTITY_JSON.copy()
    base.update(kwargs)
    return IdentityProfile(**base)


class TestIdentityGuard:
    def test_clean_tailoring_passes(self):
        identity = make_identity()
        guard = IdentityGuard(identity)
        # Tailored version keeps the company and doesn't add fake skills
        tailored = "ECOEVR Mobility. Python, Node.js, Docker, Kafka. Architected a fault-tolerant system."
        audit = guard.audit(tailored, tailored, job_skills=["Python", "Docker"])
        assert audit["passed"] is True

    def test_fabricated_skill_detected(self):
        identity = make_identity(core_skills=["Python", "Node.js"])
        guard = IdentityGuard(identity)
        original = "Python, Node.js developer"
        tailored  = original + " Kubernetes, Terraform expert"
        audit = guard.audit(original, tailored, job_skills=["Kubernetes", "Terraform"])
        assert audit["fabrication_risk"] >= 1
        assert not audit["passed"]

    def test_company_erasure_detected(self):
        identity = make_identity(companies_worked=["ECOEVR Mobility"])
        guard = IdentityGuard(identity)
        original = "Worked at ECOEVR Mobility."
        tailored  = "Worked at a mobility startup."   # company name removed
        audit = guard.audit(original, tailored, job_skills=[])
        assert not audit["passed"]

    def test_keyword_stuffing_detected(self):
        identity = make_identity()
        guard = IdentityGuard(identity)
        original = "Used Docker once."
        tailored  = "Docker Docker Docker Docker Docker Docker Docker"  # 7x
        audit = guard.audit(original, tailored, job_skills=["Docker"])
        assert audit["stuffing_risk"] >= 1

    def test_severity_high_for_fabrication(self):
        identity = make_identity(core_skills=["Python"])
        guard = IdentityGuard(identity)
        audit = guard.audit("Python dev", "Golang Rust dev ECOEVR Mobility", ["Golang", "Rust"])
        assert audit["severity"] == "high"