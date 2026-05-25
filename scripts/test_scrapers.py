"""
Live scraper smoke-test runner.

Usage examples:
  python scripts/test_scrapers.py --source greenhouse --boards stripe --limit 10
  python scripts/test_scrapers.py --source lever --companies figma --limit 10
  python scripts/test_scrapers.py --source ashby --slugs notion --limit 10
  python scripts/test_scrapers.py --source all --boards stripe --companies figma --slugs notion --limit 5

Notes:
  - This script performs real network calls to job platforms.
  - It does not write to DB, Redis, or queue; it only validates adapter scrape output.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sys
from dataclasses import asdict

import httpx

# Add project root to sys.path to allow running directly
project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.adapters.ashby import AshbyAdapter
from src.adapters.greenhouse import GreenhouseAdapter
from src.adapters.lever import LeverAdapter

logger = logging.getLogger("test_scrapers")


def _parse_csv(values: list[str] | None, default: list[str]) -> list[str]:
    if not values:
        return default
    out: list[str] = []
    for chunk in values:
        out.extend(v.strip() for v in chunk.split(",") if v.strip())
    return out or default


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run live scraper smoke tests for adapters.")
    p.add_argument(
        "--source",
        choices=["greenhouse", "lever", "ashby", "all"],
        default="all",
        help="Which adapter source to test.",
    )
    p.add_argument("--boards", nargs="*", help="Greenhouse boards, comma or space separated.")
    p.add_argument("--companies", nargs="*", help="Lever companies, comma or space separated.")
    p.add_argument("--slugs", nargs="*", help="Ashby slugs, comma or space separated.")
    p.add_argument("--limit", type=int, default=10, help="Max jobs to print per source.")
    p.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return p


async def _collect_jobs(source: str, adapter, limit: int) -> list[dict]:
    jobs: list[dict] = []
    async for job in adapter.scrape():
        jobs.append(asdict(job))
        if len(jobs) >= limit:
            break
    logger.info("%s: collected %d jobs", source, len(jobs))
    return jobs


async def main_async(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    boards = _parse_csv(args.boards, ["stripe"])
    companies = _parse_csv(args.companies, ["figma"])
    slugs = _parse_csv(args.slugs, ["notion"])

    selected = [args.source] if args.source != "all" else ["greenhouse", "lever", "ashby"]
    failures = 0

    async with httpx.AsyncClient(headers={"User-Agent": "JobAcquisitionOS-ScraperTest/1.0"}) as http:
        for source in selected:
            try:
                if source == "greenhouse":
                    adapter = GreenhouseAdapter(boards=boards, http=http)
                    target_desc = f"boards={boards}"
                elif source == "lever":
                    adapter = LeverAdapter(companies=companies, http=http)
                    target_desc = f"companies={companies}"
                elif source == "ashby":
                    adapter = AshbyAdapter(slugs=slugs, http=http)
                    target_desc = f"slugs={slugs}"
                else:
                    raise ValueError(f"Unsupported source: {source}")

                print(f"\n=== Testing {source} ({target_desc}) ===")
                healthy = await adapter.health_check()
                print(f"health_check: {healthy}")

                jobs = await _collect_jobs(source, adapter, args.limit)
                if not jobs:
                    print("No jobs returned (could be empty source, throttling, or API changes).")
                else:
                    print(json.dumps(jobs, indent=2, default=str))
            except Exception as e:
                failures += 1
                logger.exception("%s test failed: %s", source, e)

    if failures:
        print(f"\nCompleted with {failures} failing source(s).")
        return 1

    print("\nAll selected source tests completed.")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be >= 1")
    exit_code = asyncio.run(main_async(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
