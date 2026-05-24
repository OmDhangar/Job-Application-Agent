"""
tests/unit/test_identity_guard.py
tests/unit/test_strategy.py
tests/unit/test_scorer.py
"""
import pytest
from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME, SAMPLE_JD_BACKEND, SAMPLE_IDENTITY_JSON
from src.tailoring.identity_guard import IdentityGuard
from src.tailoring.strategy_generator import StrategyGenerator
from src.enrichment.jd_analyzer import JDAnalysis
from src.schemas.candidate import IdentityProfile


# ─── StrategyGenerator ────────────────────────────────────────────────────────

class TestStrategyGenerator:
    def make_jd(self, role_type="backend", seniority="mid"):
        return JDAnalysis(
            role_type=role_type,
            seniority=seniority,
            required_skills=["Python", "PostgreSQL", "Docker"],
            tech_stack=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            ats_keywords=["REST API", "microservices", "Docker"],
        )

    def test_strategy_returns_plan(self):
        gen = StrategyGenerator()
        jd = self.make_jd()
        plan = gen.generate(IdentityProfile(**SAMPLE_IDENTITY_JSON), jd, {})
        assert plan.target_role_type == "backend"
        assert isinstance(plan.ats_keywords, list)
        assert isinstance(plan.bullet_focus, list)

    def test_only_authentic_keywords(self):
        gen = StrategyGenerator()
        identity = IdentityProfile(**SAMPLE_IDENTITY_JSON)
        jd = JDAnalysis(
            role_type="backend",
            ats_keywords=["Python", "Kubernetes", "TensorFlow"],  # Kubernetes/TF not in resume
            tech_stack=["Python", "Kubernetes"],
        )
        plan = gen.generate(identity, jd, {})
        # Python is real; Kubernetes and TensorFlow should NOT appear
        for kw in plan.ats_keywords:
            assert kw in ["Python"]

    def test_research_role_adds_publications_section(self):
        gen = StrategyGenerator()
        jd = JDAnalysis(role_type="research", ats_keywords=[])
        plan = gen.generate(IdentityProfile(**SAMPLE_IDENTITY_JSON), jd, {})
        sections = [s.section for s in plan.section_weights]
        assert "publications" in sections

