"""Job-source integration contracts.

Keep every source adapter isolated and honour each source's terms of service,
robots policy, published API rate limits, and attribution requirements.
"""
from abc import ABC, abstractmethod
from typing import Any
import asyncio
import os
import re
import sys
from urllib.parse import quote_plus

class JobProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, location: str, freshness: str, company: str = "") -> list[dict[str, Any]]:
        """Return normalized JobScout job dictionaries."""

class WorkdayJobProvider(JobProvider):
    name = "Workday"

    async def search(self, query: str, location: str, freshness: str, company: str = "") -> list[dict[str, Any]]:
        if not company.strip():
            return []
        if os.getenv("JOBSCOUT_ENABLE_WORKDAY_SCRAPE", "").lower() not in {"1", "true", "yes"}:
            raise RuntimeError("Workday company-name scraping is disabled by default to avoid slow or blocked portal probes. Showing curated fallback roles.")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Workday scraping requires OPENAI_API_KEY on the backend. Showing curated fallback roles.")
        from .job_scraper import JobScrapeError, scrape_job_page, scrape_job_page_in_worker

        errors: list[str] = []
        max_candidates = int(os.getenv("JOBSCOUT_WORKDAY_MAX_CANDIDATES", "3"))
        for url in self._candidate_urls(company, query, location)[:max_candidates]:
            try:
                raw_jobs = await asyncio.to_thread(scrape_job_page_in_worker, url) if sys.platform == "win32" else await scrape_job_page(url)
                jobs = [self._normalize_job(job, index) for index, job in enumerate(raw_jobs)]
                if jobs:
                    return jobs
            except JobScrapeError as exc:
                errors.append(str(exc))
                continue
        if errors:
            raise RuntimeError("Could not resolve a public Workday portal for that company. Try the company's exact careers URL if available.")
        return []

    def _candidate_urls(self, company: str, query: str, location: str) -> list[str]:
        slug = re.sub(r"[^a-z0-9]+", "", company.lower())
        dashed_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
        search = quote_plus(" ".join(part for part in [query, location] if part.strip()))
        tenant_slugs = [slug, dashed_slug] if slug != dashed_slug else [slug]
        hosts = ["wd1", "wd2", "wd3", "wd5"]
        paths = ["en-US/External", "en-US/Careers", "en-US/jobs", "en-US/Jobs"]
        candidates: list[str] = []
        for tenant in tenant_slugs:
            if not tenant:
                continue
            for host in hosts:
                for path in paths:
                    suffix = f"?q={search}" if search else ""
                    candidates.append(f"https://{tenant}.{host}.myworkdayjobs.com/{path}{suffix}")
        return candidates[:12]

    def _normalize_job(self, job: dict[str, Any], index: int) -> dict[str, Any]:
        title = str(job.get("job_title") or "Workday role")
        company = str(job.get("company_name") or "Company")
        url = str(job.get("application_url") or "#")
        skills = [str(skill) for skill in job.get("required_skills", [])][:5]
        return {
            "id": f"workday-{abs(hash(url or title))}-{index}",
            "title": title,
            "company": company,
            "location": str(job.get("location") or "Not specified"),
            "mode": self._mode_from_location(str(job.get("location") or "")),
            "posted": "Workday",
            "salary": "Not listed",
            "match": 78,
            "tags": skills or ["Workday"],
            "source": self.name,
            "description": str(job.get("job_description_summary") or "Public Workday job listing."),
            "url": url,
        }

    def _mode_from_location(self, location: str) -> str:
        lowered = location.lower()
        if "remote" in lowered:
            return "Remote"
        if "hybrid" in lowered:
            return "Hybrid"
        return "On-site"

class ProviderRegistry:
    def __init__(self, providers: list[JobProvider] | None = None):
        self.providers = providers or []

    async def search_all(self, query: str, location: str, freshness: str, company: str = "") -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for provider in self.providers:
            results.extend(await provider.search(query, location, freshness, company))
        # URLs are a stable cross-source key when available.
        return list({job.get("url", job["id"]): job for job in results}.values())
