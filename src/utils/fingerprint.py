"""
src/utils/fingerprint.py

Deterministic fingerprinting utilities for strings, payloads, and files.
Used for caching, deduplication, and integrity checks.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_string(text: str) -> str:
    """Generate SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    """Generate SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_dict(payload: dict[str, Any]) -> str:
    """
    Generate deterministic SHA-256 hex digest of a dictionary.
    Keys are sorted to guarantee consistency across identical content.
    """
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hash_string(serialized)


def hash_file(file_path: str) -> str:
    """
    Generate SHA-256 hex digest of a local file.
    Reads in 64KB chunks to optimize memory usage for large files.
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()
