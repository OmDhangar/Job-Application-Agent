"""
src/tailoring/latex_compiler.py

Local LaTeX → PDF compilation using pdflatex.
Runs entirely offline — zero API cost.
pdflatex must be installed: `sudo apt install texlive-full`
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Required LaTeX packages for the resume template
_REQUIRED_PACKAGES = [
    "latexsym", "fullpage", "titlesec", "marvosym", "enumitem",
    "hyperref", "fancyhdr", "babel", "tabularx",
]


class LatexCompiler:
    """
    Compiles LaTeX source to PDF using pdflatex.
    Runs twice to resolve cross-references (titles, sections).
    Returns (pdf_bytes, log) — pdf_bytes is None on failure.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._pdflatex = shutil.which("pdflatex")
        if not self._pdflatex:
            logger.warning(
                "pdflatex not found. Install: sudo apt install texlive-full. "
                "PDF output will be disabled."
            )

    @property
    def available(self) -> bool:
        return self._pdflatex is not None

    def compile(self, latex_source: str) -> tuple[bytes | None, str]:
        """
        Compile LaTeX string to PDF.

        Returns:
            (pdf_bytes, compile_log)
            pdf_bytes is None if compilation fails or pdflatex unavailable.
        """
        if not self.available:
            return None, "pdflatex not available"

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / "resume.tex"
            pdf_path = Path(tmpdir) / "resume.pdf"
            log_path = Path(tmpdir) / "resume.log"

            tex_path.write_text(latex_source, encoding="utf-8")

            # Run pdflatex twice (resolves section refs)
            for run in range(2):
                result = subprocess.run(
                    [
                        self._pdflatex,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-output-directory", tmpdir,
                        str(tex_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir,
                )
                if result.returncode != 0 and run == 1:
                    log = log_path.read_text(errors="ignore") if log_path.exists() else result.stdout
                    logger.error("pdflatex failed (run %d): %s", run + 1, log[-500:])
                    return None, log

            if not pdf_path.exists():
                return None, "PDF not generated despite exit code 0"

            pdf_bytes = pdf_path.read_bytes()
            log = log_path.read_text(errors="ignore") if log_path.exists() else ""
            logger.info("PDF compiled successfully — %d bytes", len(pdf_bytes))
            return pdf_bytes, log

    def validate_latex(self, source: str) -> list[str]:
        """
        Quick structural validation before attempting compilation.
        Returns list of issues (empty = likely compilable).
        """
        issues: list[str] = []
        if r"\documentclass" not in source:
            issues.append("Missing \\documentclass")
        if r"\begin{document}" not in source:
            issues.append("Missing \\begin{document}")
        if r"\end{document}" not in source:
            issues.append("Missing \\end{document}")
        # Check balanced braces
        if source.count("{") != source.count("}"):
            issues.append(
                f"Unbalanced braces: {source.count('{')} open, {source.count('}')} close"
            )
        return issues