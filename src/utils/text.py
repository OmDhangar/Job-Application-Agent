"""
src/utils/text.py

Text processing utilities used across the codebase.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


def clean_whitespace(text: str) -> str:
    """Collapse multiple whitespace runs and strip leading/trailing."""
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, max_length: int = 500, suffix: str = "…") -> str:
    """Truncate text to *max_length* chars, appending *suffix* if clipped."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def strip_html(html: str) -> str:
    """Remove HTML tags and decode entities (lightweight, no lxml needed)."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return clean_whitespace(text)


def normalize_unicode(text: str) -> str:
    """Normalize to NFC form — prevents invisible-char mismatches."""
    return unicodedata.normalize("NFC", text)


def extract_emails(text: str) -> list[str]:
    """Return all email addresses found in *text*."""
    return re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)


def extract_urls(text: str) -> list[str]:
    """Return all HTTP(S) URLs found in *text*."""
    return re.findall(r"https?://[^\s<>\"']+", text)


def bullet_to_list(text: str) -> list[str]:
    """Split bullet-pointed text into individual items."""
    lines = re.split(r"\n\s*[•\-\*]\s*", text)
    return [line.strip() for line in lines if line.strip()]


def snake_case(text: str) -> str:
    """Convert a string to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return re.sub(r"[-\s]+", "_", s).lower()


def word_count(text: str) -> int:
    """Count whitespace-delimited words."""
    return len(text.split())


def extract_years_experience(text: str) -> Optional[float]:
    """
    Attempt to parse a years-of-experience number from freeform text.
    Matches patterns like '5+ years', '3-5 years', '2 yrs'.
    """
    match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None
