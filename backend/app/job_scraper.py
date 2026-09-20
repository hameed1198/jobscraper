"""Crawl4AI + OpenAI extraction for public job-detail pages.

This module intentionally crawls only public HTTP(S) endpoints, respects
robots.txt, and never bypasses authentication or access controls.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import socket
import sys
from typing import Any
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class JobPosting(BaseModel):
    """The strict, normalized job record returned by the extractor."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    job_title: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=250)
    job_description_summary: str = Field(min_length=1, max_length=1_500)
    application_url: HttpUrl
    required_skills: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("job_description_summary")
    @classmethod
    def summary_is_at_most_three_sentences(cls, value: str) -> str:
        # Deliberately simple and predictable validation; abbreviations do not
        # meaningfully affect the user-facing maximum.
        sentences = [part.strip() for part in value.replace("!", ".").replace("?", ".").split(".") if part.strip()]
        if len(sentences) > 3:
            raise ValueError("job_description_summary must have at most 3 sentences")
        return value

    @field_validator("required_skills")
    @classmethod
    def unique_skills(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        return [skill for skill in value if skill and not (normalized := skill.lower()) in seen and not seen.add(normalized)]


class JobScrapeError(RuntimeError):
    """A safe error surface for crawler, network, and extraction failures."""


def _normalize_url_input(url: str) -> str:
    """Accept plain URLs and Markdown links copied from chat."""
    cleaned = url.strip()
    markdown_match = re.fullmatch(r"\[([^\]]+)]\(([^)]+)\)", cleaned)
    if markdown_match:
        cleaned = markdown_match.group(2).strip()
    return cleaned


async def _assert_public_http_url(url: str) -> None:
    """Prevent SSRF when this function is exposed through an API endpoint."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise JobScrapeError("Only absolute public http(s) URLs may be scraped.")
    if parsed.username or parsed.password:
        raise JobScrapeError("URLs containing credentials are not allowed.")
    try:
        addresses = await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, parsed.hostname, None)
        for address in {entry[4][0] for entry in addresses}:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise JobScrapeError("Private, loopback, and reserved network addresses are not allowed.")
    except socket.gaierror as exc:
        raise JobScrapeError("The job-page hostname could not be resolved.") from exc


def _parse_extraction(payload: str | None, fallback_url: str) -> list[dict[str, Any]]:
    if not payload:
        return []
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise JobScrapeError("The AI extractor returned invalid JSON.") from exc
    candidates = raw if isinstance(raw, list) else [raw]
    valid: list[dict[str, Any]] = []
    extraction_errors: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("error") is True:
            message = candidate.get("content") or candidate.get("message") or "The AI extractor failed on one content block."
            extraction_errors.append(str(message))
            continue
        if isinstance(candidate.get("content"), str) and not any(field in candidate for field in JobPosting.model_fields):
            try:
                nested = json.loads(candidate["content"])
                candidate = nested if isinstance(nested, dict) else candidate
            except json.JSONDecodeError:
                pass
        # Crawl4AI annotates each extracted block with crawler metadata. Keep
        # the public API schema strict while ignoring those internal fields.
        candidate = {key: value for key, value in candidate.items() if key in JobPosting.model_fields}
        candidate.setdefault("application_url", fallback_url)
        try:
            valid.append(JobPosting.model_validate(candidate).model_dump(mode="json"))
        except ValueError:
            # One malformed object should not discard valid listings on a page.
            continue
    if not valid and extraction_errors:
        raise JobScrapeError(f"The AI extractor failed: {extraction_errors[0]}")
    return valid


def _company_name_from_page(url: str, metadata: dict[str, Any] | None) -> str:
    title = str((metadata or {}).get("title") or "").strip()
    match = re.search(r"(?:jobs|careers|openings)\s+at\s+(.+)", title, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" -|")
    parsed = urlparse(url)
    host_parts = (parsed.hostname or "Unknown company").replace("www.", "").split(".")
    return host_parts[-2].replace("-", " ").title() if len(host_parts) >= 2 else host_parts[0].title()


def _clean_job_link_text(text: str) -> str:
    return " ".join(text.split()).strip(" -|")


def _location_from_title(title: str) -> str:
    lowered = title.lower()
    if "remote" in lowered:
        return "Remote"
    if "hybrid" in lowered:
        return "Hybrid"
    if "onsite" in lowered or "on-site" in lowered:
        return "Onsite"
    return "Not specified"


def _fallback_jobs_from_links(url: str, metadata: dict[str, Any] | None, links: dict[str, list[dict[str, Any]]] | None) -> list[dict[str, Any]]:
    """Return real job-listing links when semantic extraction returns nothing.

    This is intentionally conservative: it only recognizes common public ATS
    URL patterns. Detailed summaries and skills still come from the LLM when a
    job-detail page is scraped.
    """
    parsed_source = urlparse(url)
    company_name = _company_name_from_page(url, metadata)
    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []
    for link in (links or {}).get("internal", []) + (links or {}).get("external", []):
        raw_href = str(link.get("href") or "").strip()
        title = _clean_job_link_text(str(link.get("text") or link.get("title") or ""))
        if not raw_href or not title:
            continue
        absolute_url = urljoin(url, raw_href)
        parsed_href = urlparse(absolute_url)
        path = parsed_href.path.strip("/")
        is_greenhouse_job = parsed_href.hostname == "job-boards.greenhouse.io" and len(path.split("/")) >= 2
        is_ashby_job = parsed_href.hostname == "jobs.ashbyhq.com" and len(path.split("/")) >= 2
        is_workday_job = bool(parsed_href.hostname and (parsed_href.hostname.endswith("myworkdayjobs.com") or parsed_href.hostname.endswith("myworkday.com")) and any(marker in path.lower() for marker in ("/job/", "job_", "requisition", "req")))
        same_public_careers_link = parsed_href.hostname == parsed_source.hostname and any(
            marker in path.lower() for marker in ("job", "career", "opening", "position", "requisition")
        )
        if not (is_greenhouse_job or is_ashby_job or is_workday_job or same_public_careers_link):
            continue
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        try:
            jobs.append(
                JobPosting.model_validate(
                    {
                        "job_title": title[:200],
                        "company_name": company_name,
                        "location": _location_from_title(title),
                        "job_description_summary": "Public job listing discovered from the careers page. Scrape the job detail URL for a richer summary and required skills.",
                        "application_url": absolute_url,
                        "required_skills": [],
                    }
                ).model_dump(mode="json")
            )
        except ValueError:
            continue
    return jobs


async def scrape_job_page(url: str) -> list[dict]:
    """Extract one or more jobs from a dynamic, public job-detail/listing page.

    Requires `OPENAI_API_KEY` in the backend environment. Crawl4AI's browser
    waits for network idle, scrolls appended infinite content, removes common
    overlays, prunes boilerplate, then sends fit Markdown to gpt-4o-mini.
    """
    url = _normalize_url_input(url)
    await _assert_public_http_url(url)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise JobScrapeError("OPENAI_API_KEY is not configured on the backend.")

    # Imported here so the existing FastAPI server can still start before the
    # optional production crawler dependency has been installed.
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    except ImportError as exc:
        raise JobScrapeError("Crawl4AI is not installed. Run: pip install -r requirements.txt") from exc

    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=api_key, backoff_max_attempts=3),
        schema=JobPosting.model_json_schema(),
        extraction_type="schema",
        input_format="fit_markdown",
        chunk_token_threshold=1_500,
        overlap_rate=0.0,
        verbose=True,
        instruction=(
            "Extract every genuine job posting from this public careers page. "
            "Ignore site navigation, cookie banners, marketing copy, equal-opportunity boilerplate, and unrelated roles. "
            "Return only schema-valid objects. Give a concise role summary of no more than three sentences. "
            "For location explicitly state Remote, Hybrid, or Onsite when the page provides it. "
            f"Use {url} as application_url only when a direct apply link is not visible."
        ),
    )
    markdown_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.45, threshold_type="dynamic", min_word_threshold=25),
        options={"ignore_links": False},
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle",
        wait_for="css:body",
        page_timeout=45_000,
        wait_for_timeout=15_000,
        delay_before_return_html=1.0,
        scan_full_page=True,
        max_scroll_steps=20,
        scroll_delay=0.4,
        remove_overlay_elements=True,
        remove_consent_popups=True,
        excluded_tags=["nav", "footer", "header", "script", "style", "noscript"],
        excluded_selector="[class*='cookie'], [id*='cookie'], [class*='banner'], [class*='modal']",
        word_count_threshold=20,
        check_robots_txt=True,
        simulate_user=True,
        override_navigator=True,
        markdown_generator=markdown_generator,
        extraction_strategy=llm_strategy,
    )
    browser_config = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        viewport_width=1440,
        viewport_height=1000,
        user_agent_mode="random",
        enable_stealth=True,
        avoid_ads=True,
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
    except TimeoutError as exc:
        raise JobScrapeError("Timed out while loading the job page.") from exc
    except Exception as exc:
        raise JobScrapeError("Could not load the job page. Please try again later.") from exc
    finally:
        llm_strategy.show_usage()

    if not result.success:
        raise JobScrapeError(result.error_message or "Crawler failed to load the job page.")
    jobs = _parse_extraction(result.extracted_content, url)
    if jobs:
        return jobs
    return _fallback_jobs_from_links(url, result.metadata, result.links)


def scrape_job_page_in_worker(url: str) -> list[dict]:
    """Run Playwright in a subprocess-capable event loop on Windows.

    Uvicorn's Windows reload supervisor uses SelectorEventLoop, which cannot
    create subprocesses. Playwright launches Chromium as a subprocess, so the
    crawl must run in this dedicated Proactor loop instead.
    """
    if sys.platform == "win32":
        loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
    else:
        loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(scrape_job_page(url))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        asyncio.set_event_loop(None)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.job_scraper https://public-careers-page.example/jobs")
    try:
        print(json.dumps(asyncio.run(scrape_job_page(sys.argv[1])), indent=2))
    except JobScrapeError as error:
        raise SystemExit(f"Scrape failed: {error}") from error
