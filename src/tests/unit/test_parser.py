"""
tests/unit/test_parser.py  —  ResumeParser unit tests.
"""
import pytest
from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME
from src.tailoring.parser import ResumeParser, _latex_to_plain


class TestResumeParser:
    def setup_method(self):
        self.parser = ResumeParser()

    def test_tex_extraction_returns_tuple(self):
        raw = SAMPLE_LATEX_RESUME.encode("utf-8")
        plain, latex = self.parser.extract(raw, "resume.tex")
        assert isinstance(plain, str)
        assert isinstance(latex, str)
        assert len(plain) > 50

    def test_tex_preserves_raw_latex(self):
        raw = SAMPLE_LATEX_RESUME.encode("utf-8")
        _, latex = self.parser.extract(raw, "resume.tex")
        assert r"\documentclass" in latex
        assert r"\begin{document}" in latex

    def test_tex_plain_text_contains_name(self):
        raw = SAMPLE_LATEX_RESUME.encode("utf-8")
        plain, _ = self.parser.extract(raw, "resume.tex")
        assert "Om Dhangar" in plain

    def test_tex_plain_text_contains_skills(self):
        raw = SAMPLE_LATEX_RESUME.encode("utf-8")
        plain, _ = self.parser.extract(raw, "resume.tex")
        assert "Node.js" in plain or "Python" in plain

    def test_non_tex_returns_none_latex(self):
        raw = b"Fake PDF content"
        _, latex = self.parser.extract(raw, "resume.pdf")
        assert latex is None

    def test_caching_is_consistent(self):
        raw = SAMPLE_LATEX_RESUME.encode("utf-8")
        result1 = self.parser.extract(raw, "resume.tex")
        result2 = self.parser.extract(raw, "resume.tex")
        assert result1[0] == result2[0]


def test_latex_to_plain_strips_commands():
    latex = r"\textbf{Hello} \textit{World}"
    result = _latex_to_plain(latex)
    assert "Hello" in result
    assert "World" in result
    assert r"\textbf" not in result


def test_latex_to_plain_handles_resume_items():
    latex = r"\resumeItem{Built a scalable API using FastAPI}"
    result = _latex_to_plain(latex)
    assert "Built a scalable API" in result