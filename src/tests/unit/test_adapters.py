"""
tests/unit/test_adapters.py  —  Adapter unit tests (no network required).
tests/unit/test_deduplicator.py  —  Deduplicator logic tests.
"""
import pytest
from datetime import datetime, timezone
from src.adapters.base import CanonicalJob
from src.adapters.greenhouse import GreenhouseAdapter
from src.adapters.lever import LeverAdapter
from src.adapters.ashby import AshbyAdapter


# ─── CanonicalJob ─────────────────────────────────────────────────────────────

class TestCanonicalJob:
    def test_fingerprint_is_deterministic(self):
        job = CanonicalJob(
            title="Backend Engineer",
            company_name="Acme",
            source="greenhouse",
            source_url="https://example.com/job/1",
            description="...",
            source_id="12345",
        )
        fp1 = job.fingerprint
        fp2 = job.fingerprint
        assert fp1 == fp2

    def test_fingerprint_differs_across_sources(self):
        base = dict(
            title="Engineer", company_name="Co",
            source_url="https://x.com", description="",
        )
        j1 = CanonicalJob(**base, source="greenhouse", source_id="1")
        j2 = CanonicalJob(**base, source="lever",      source_id="1")
        assert j1.fingerprint != j2.fingerprint

    def test_fingerprint_is_sha256_hex(self):
        job = CanonicalJob(
            title="SWE", company_name="Co", source="ashby",
            source_url="https://x.com", description="", source_id="abc",
        )
        fp = job.fingerprint
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ─── Greenhouse transform ─────────────────────────────────────────────────────

class TestGreenhouseAdapter:
    def test_transform_produces_canonical_job(self):
        raw = {
            "id": 9999,
            "title": "Senior Python Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/9999",
            "location": {"name": "Remote — US"},
            "content": "We are looking for a Python engineer...",
            "updated_at": "2025-01-15T10:00:00Z",
        }
        adapter = GreenhouseAdapter.__new__(GreenhouseAdapter)
        adapter.source_name = "greenhouse"
        job = adapter._transform(raw, "acme")
        assert job.title == "Senior Python Engineer"
        assert job.source == "greenhouse"
        assert job.remote_type == "remote"
        assert isinstance(job.posted_at, datetime)
        assert job.company_domain == "acme.com"

    def test_transform_handles_missing_fields(self):
        raw = {"id": 1, "title": "Engineer", "absolute_url": "", "location": {}, "content": ""}
        adapter = GreenhouseAdapter.__new__(GreenhouseAdapter)
        adapter.source_name = "greenhouse"
        job = adapter._transform(raw, "company")
        assert job.title == "Engineer"
        assert job.location == ""


# ─── Lever transform ──────────────────────────────────────────────────────────

class TestLeverAdapter:
    def test_transform_produces_canonical_job(self):
        raw = {
            "id": "lever-123",
            "text": "Data Engineer",
            "hostedUrl": "https://jobs.lever.co/stripe/lever-123",
            "descriptionPlain": "We need a data engineer.",
            "categories": {"location": "San Francisco", "commitment": "Full-time", "level": "Senior"},
            "createdAt": 1700000000000,
        }
        adapter = LeverAdapter.__new__(LeverAdapter)
        adapter.source_name = "lever"
        job = adapter._transform(raw, "stripe")
        assert job.title == "Data Engineer"
        assert job.seniority == "Senior"
        assert job.source_id == "lever-123"
        assert isinstance(job.posted_at, datetime)