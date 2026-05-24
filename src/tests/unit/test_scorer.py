"""
tests/unit/test_identity_guard.py
tests/unit/test_strategy.py
tests/unit/test_scorer.py
"""
import pytest
from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME, SAMPLE_JD_BACKEND, SAMPLE_IDENTITY_JSON
from src.tailoring.identity_guard import IdentityGuard
from src.tailoring.strategy_generator import StrategyGenerator
from src.tailoring.scorer import ResumeScorer
from src.enrichment.jd_analyzer import JDAnalysis
from src.schemas.candidate import IdentityProfile



# ─── ResumeScorer ─────────────────────────────────────────────────────────────

class TestResumeScorer:
    def make_jd(self):
        return JDAnalysis(
            ats_keywords=["Python", "Docker", "PostgreSQL", "REST API"],
            tech_stack=["Python", "Docker"],
        )

    def test_scores_are_floats_in_range(self):
        scorer = ResumeScorer()
        identity = IdentityProfile(**SAMPLE_IDENTITY_JSON)
        jd = self.make_jd()
        resume = "Python Docker PostgreSQL REST API ECOEVR Mobility built scaled optimized 40% faster 20ms"
        critique = "Score: 7/10\n1. Strong technical skills..."
        scores = scorer.score(resume, jd, identity, critique)
        for field in ["ats_score", "authenticity_score", "recruiter_readability",
                      "technical_credibility", "interview_probability", "composite"]:
            val = getattr(scores, field)
            assert 0 <= val <= 100, f"{field}={val} out of range"

    def test_more_ats_keywords_raise_ats_score(self):
        scorer = ResumeScorer()
        identity = IdentityProfile(**SAMPLE_IDENTITY_JSON)
        jd = self.make_jd()
        critique = "7/10"
        sparse  = scorer.score("Generic engineer", jd, identity, critique)
        rich    = scorer.score("Python Docker PostgreSQL REST API ECOEVR Mobility", jd, identity, critique)
        assert rich.ats_score >= sparse.ats_score

    def test_quantified_bullets_raise_credibility(self):
        scorer = ResumeScorer()
        identity = IdentityProfile(**SAMPLE_IDENTITY_JSON)
        jd = self.make_jd()
        critique = "7/10"
        vague  = scorer.score("Built things ECOEVR Mobility", jd, identity, critique)
        quant  = scorer.score("Reduced latency by 40% ECOEVR Mobility. Processed 5TB daily.", jd, identity, critique)
        assert quant.technical_credibility >= vague.technical_credibility