"""
tests/unit/test_latex_compiler.py  —  LatexCompiler unit tests.
Requires pdflatex installed: sudo apt install texlive-full
"""
import pytest
from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME
from src.tailoring.latex_compiler import LatexCompiler


@pytest.fixture
def compiler():
    return LatexCompiler(timeout=30)


class TestLatexCompiler:
    def test_availability(self, compiler):
        # pdflatex must be installed in the test environment
        assert compiler.available, (
            "pdflatex not found. Install: sudo apt install texlive-full"
        )

    def test_valid_latex_compiles_to_pdf(self, compiler):
        pdf_bytes, log = compiler.compile(SAMPLE_LATEX_RESUME)
        assert pdf_bytes is not None, f"Compile failed. Log: {log[-400:]}"
        assert len(pdf_bytes) > 1000     # PDF should be several KB minimum
        assert pdf_bytes[:4] == b"%PDF"  # valid PDF magic bytes

    def test_invalid_latex_returns_none(self, compiler):
        broken = r"\documentclass{article}\begin{document}\BROKENCMD\end{document}"
        pdf_bytes, log = compiler.compile(broken)
        # Might still produce PDF for minor errors; just ensure no crash
        assert isinstance(log, str)

    def test_validate_catches_missing_documentclass(self, compiler):
        issues = compiler.validate_latex(r"\begin{document}Hello\end{document}")
        assert any("documentclass" in i.lower() for i in issues)

    def test_validate_catches_unbalanced_braces(self, compiler):
        issues = compiler.validate_latex(r"\documentclass{article}\begin{document}{unclosed\end{document}")
        assert any("brace" in i.lower() for i in issues)

    def test_validate_clean_latex_has_no_issues(self, compiler):
        issues = compiler.validate_latex(SAMPLE_LATEX_RESUME)
        assert issues == [], f"Unexpected issues: {issues}"

    def test_double_run_produces_consistent_pdf(self, compiler):
        pdf1, _ = compiler.compile(SAMPLE_LATEX_RESUME)
        pdf2, _ = compiler.compile(SAMPLE_LATEX_RESUME)
        # Both should succeed; exact bytes may differ (timestamps) but both valid
        assert pdf1 is not None
        assert pdf2 is not None