"""
src/tailoring/parser.py

Resume text and LaTeX extraction.
Supports: .pdf  .docx  .tex  .txt
All local — zero API cost.
Results are in-process cached by file SHA-256.
"""
from __future__ import annotations

import hashlib
import logging
import re
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

# in-process cache: sha256 → (plain_text, raw_latex_or_None)
_CACHE: dict[str, tuple[str, str | None]] = {}


class ResumeParser:
    """
    Returns:
        plain_text  — always available; used for identity extraction and scoring
        raw_latex   — only for .tex input; preserved for structure-aware tailoring
    """

    def extract(
        self, raw_bytes: bytes, filename: str
    ) -> tuple[str, str | None]:
        """
        Returns (plain_text, raw_latex).
        raw_latex is only non-None when the source is a .tex file.
        """
        key = hashlib.sha256(raw_bytes).hexdigest()
        if key in _CACHE:
            logger.debug("Resume parse cache hit")
            return _CACHE[key]

        fname = Path(filename).suffix.lower()
        if fname == ".tex":
            result = self._from_tex(raw_bytes)
        elif fname == ".pdf":
            result = (self._from_pdf(raw_bytes), None)
        elif fname == ".docx":
            result = (self._from_docx(raw_bytes), None)
        else:
            result = (raw_bytes.decode("utf-8", errors="ignore"), None)

        _CACHE[key] = result
        return result

    # ─── Format handlers ─────────────────────────────────────────────────────

    def _from_tex(self, data: bytes) -> tuple[str, str]:
        raw_latex = data.decode("utf-8", errors="ignore")
        plain = _latex_to_plain(raw_latex)
        return plain, raw_latex

    def _from_pdf(self, data: bytes) -> str:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(BytesIO(data))
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages)
        except Exception as e:
            logger.error("PDF extraction failed: %s", e)
            return data.decode("utf-8", errors="ignore")

    def _from_docx(self, data: bytes) -> str:
        try:
            from docx import Document
            doc = Document(BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.error("DOCX extraction failed: %s", e)
            return data.decode("utf-8", errors="ignore")


def _latex_to_plain(latex: str) -> str:
    """
    Convert LaTeX source to readable plain text for NLP / scoring.
    Not perfect — good enough for identity extraction and ATS scoring.
    """
    # Remove comments
    text = re.sub(r"%.*", "", latex)
    # Unwrap common resume commands
    text = re.sub(r"\\resumeItem\{([^}]*)\}", r"• \1", text)
    text = re.sub(r"\\resumeSubheading\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}",
                  r"\1  \2\n\3  \4", text)
    text = re.sub(r"\\resumeProjectHeading\{([^}]*)\}\{([^}]*)\}", r"\1  \2", text)
    # Unwrap remaining commands with one arg
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)
    # Remove commands with no args
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    # Remove braces, environments
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()