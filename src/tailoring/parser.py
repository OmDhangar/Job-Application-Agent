"""
src/tailoring/parser.py

Resume text extraction from PDF and DOCX.
100% local — no API calls. Cached by file hash.
"""
from __future__ import annotations

import hashlib
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

_CACHE: dict[str, str] = {}  # in-process cache; use Redis in multi-worker setup


class ResumeParser:
    def extract(self, raw_bytes: bytes, filename: str) -> str:
        cache_key = hashlib.sha256(raw_bytes).hexdigest()
        if cache_key in _CACHE:
            logger.debug("Resume parse cache hit")
            return _CACHE[cache_key]

        text = self._extract(raw_bytes, filename)
        _CACHE[cache_key] = text
        return text

    def _extract(self, raw_bytes: bytes, filename: str) -> str:
        fname = filename.lower()
        try:
            if fname.endswith(".pdf"):
                return self._from_pdf(raw_bytes)
            elif fname.endswith(".docx"):
                return self._from_docx(raw_bytes)
            else:
                return raw_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error("Resume extraction error: %s", e)
            return raw_bytes.decode("utf-8", errors="ignore")

    def _from_pdf(self, data: bytes) -> str:
        import PyPDF2
        reader = PyPDF2.PdfReader(BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages)

    def _from_docx(self, data: bytes) -> str:
        from docx import Document
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
