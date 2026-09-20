import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .providers import ProviderRegistry, WorkdayJobProvider

load_dotenv()
app = FastAPI(title="JobScout API", version="0.2.0")
cors_origins = [origin.strip() for origin in os.getenv("JOBSCOUT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_origin_regex=r"https://[a-zA-Z0-9-]+\.github\.io", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
providers = ProviderRegistry([WorkdayJobProvider()])

class SearchRequest(BaseModel):
    query: str = "Frontend Engineer"
    company: str = ""
    location: str = "India"
    mode: str = "Any"
    freshness: str = "Last 24 hours"

class MatchRequest(BaseModel):
    resume_text: str
    job_description: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthUser(BaseModel):
    name: str
    email: str
    initials: str

class ScrapePageRequest(BaseModel):
    url: str

AUTH_USER = AuthUser(
    name=os.getenv("JOBSCOUT_USER_NAME", "Hameed Khan"),
    email=os.getenv("JOBSCOUT_USER_EMAIL", "hameed@example.com"),
    initials=os.getenv("JOBSCOUT_USER_INITIALS", "HK")
)
AUTH_PASSWORD = os.getenv("JOBSCOUT_USER_PASSWORD", "jobscout2026")
AUTH_SECRET = os.getenv("JOBSCOUT_AUTH_SECRET", "local-jobscout-dev-secret")
AUTH_TOKEN_TTL_SECONDS = 60 * 60 * 8

def _sign_token(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{body}.{encoded_signature}"

def _read_token(token: str) -> dict:
    try:
        body, encoded_signature = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(encoded_signature, expected):
            raise ValueError("Bad signature")
        padded_body = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_body.encode()))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid session")
    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Session expired")
    return payload

def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing session")
    payload = _read_token(authorization.removeprefix("Bearer ").strip())
    if payload.get("email") != AUTH_USER.email:
        raise HTTPException(status_code=401, detail="Invalid session")
    return AUTH_USER

STOP_WORDS = {
    "a", "about", "above", "across", "after", "again", "against", "all", "also", "am", "an", "and", "any", "are", "as", "at", "be", "because", "been", "being", "by", "can", "could", "did", "do", "does", "doing", "for", "from", "had", "has", "have", "having", "he", "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "job", "more", "most", "must", "of", "on", "or", "our", "ours", "role", "she", "should", "so", "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "those", "through", "to", "under", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "will", "with", "within", "would", "you", "your",
    "ability", "applications", "application", "basic", "basics", "business", "clean", "code", "collaborate", "description", "develop", "developer", "development", "experienced", "experience", "including", "looking", "need", "overview", "required", "requirements", "responsibilities", "responsibility", "strong", "team", "using", "work", "working"
}

KEYWORD_ALIASES = {
    "django rest framework": "drf",
    "restful": "rest",
    "postgresql": "postgres",
    "javascript": "js",
    "typescript": "ts"
}

def extract_keywords(text: str) -> set[str]:
    normalized = text.lower()
    for phrase, alias in KEYWORD_ALIASES.items():
        normalized = normalized.replace(phrase, f" {alias} ")
    return {
        token
        for raw_token in re.findall(r"[a-z][a-z0-9+#.\-]*", normalized)
        for token in [raw_token.strip(".-")]
        if len(token) > 2 and token not in STOP_WORDS
    }

def demo_jobs(filters: SearchRequest):
    jobs = [
    {"id":"1","title":"Senior Frontend Engineer","company":"Vercel","location":"Remote · India","mode":"Remote","posted":"2h ago","salary":"₹32L – ₹48L","match":94,"tags":["React","TypeScript","Next.js"],"source":"Company careers","description":"Build delightful developer tools and high-performance web experiences.","url":"https://vercel.com/careers"},
    {"id":"2","title":"Full Stack Developer","company":"Razorpay","location":"Bengaluru, India","mode":"Hybrid","posted":"5h ago","salary":"₹20L – ₹35L","match":88,"tags":["React","Python","FastAPI"],"source":"Company careers","description":"Create reliable products used by millions of businesses every day.","url":"https://razorpay.com/jobs/"},
    {"id":"3","title":"Software Engineer, Web","company":"Postman","location":"Remote · India","mode":"Remote","posted":"1d ago","salary":"₹24L – ₹40L","match":82,"tags":["React","Node.js","Design systems"],"source":"Company careers","description":"Shape collaboration tools for the global API-first community.","url":"https://www.postman.com/company/careers/"},
    {"id":"4","title":"Data Engineer","company":"Atlassian","location":"Remote · India","mode":"Remote","posted":"6h ago","salary":"₹28L – ₹44L","match":91,"tags":["Python","SQL","Spark","Airflow"],"source":"Company careers","description":"Build reliable data pipelines, warehouse models, and analytics-ready datasets for product and business teams.","url":"https://www.atlassian.com/company/careers"},
    {"id":"5","title":"Senior Data Engineer","company":"Stripe","location":"Bengaluru, India","mode":"Hybrid","posted":"1d ago","salary":"₹34L – ₹55L","match":89,"tags":["Python","ETL","Kafka","Snowflake"],"source":"Company careers","description":"Design scalable data infrastructure, streaming pipelines, and governed datasets for financial product insights.","url":"https://stripe.com/jobs"},
    ]
    query_words = [word for word in extract_keywords(filters.query) if len(word) > 1]
    location_words = [word for word in filters.location.lower().split() if len(word) > 1]
    freshness_hours = {"Last 24 hours": 24, "Last 3 days": 72, "Last 7 days": 168}
    def age_in_hours(posted: str) -> int:
        if "h" in posted: return int(posted.split("h")[0])
        if "d" in posted: return int(posted.split("d")[0]) * 24
        return 10_000
    def matches(job: dict) -> bool:
        haystack = " ".join([job["title"], job["company"], job["description"], *job["tags"]]).lower()
        search_match = not query_words or all(word in haystack for word in query_words)
        location_match = not location_words or any(word in job["location"].lower() for word in location_words)
        mode_match = filters.mode == "Any" or job["mode"] == filters.mode
        fresh_match = age_in_hours(job["posted"]) <= freshness_hours.get(filters.freshness, 10_000)
        return search_match and location_match and mode_match and fresh_match
    return [job for job in jobs if matches(job)]

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/api/auth/login")
def login(request: LoginRequest):
    if request.email.strip().lower() != AUTH_USER.email.lower() or not hmac.compare_digest(request.password, AUTH_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = _sign_token({"email": AUTH_USER.email, "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS})
    return {"token": token, "user": AUTH_USER}

@app.get("/api/auth/me")
def me(user: AuthUser = Depends(current_user)):
    return {"user": user}

@app.post("/api/auth/logout")
def logout():
    return {"ok": True}

@app.post("/api/jobs/search")
async def search_jobs(filters: SearchRequest):
    warning = ""
    provider_jobs: list[dict] = []
    if filters.company.strip():
        try:
            provider_jobs = await providers.search_all(filters.query, filters.location, filters.freshness, filters.company)
        except RuntimeError as exc:
            warning = str(exc)
    jobs = provider_jobs or demo_jobs(filters)
    if filters.company.strip() and not provider_jobs and not warning:
        warning = "No Workday jobs were found for that company. Showing curated fallback roles."
    return {"jobs": jobs, "warning": warning}

@app.post("/api/jobs/scrape-page")
async def scrape_page(request: ScrapePageRequest):
    """Extract public career-page listings with Crawl4AI and gpt-4o-mini."""
    from .job_scraper import JobScrapeError, scrape_job_page, scrape_job_page_in_worker
    try:
        # Playwright cannot launch Chromium from Uvicorn's Windows selector
        # loop (used by --reload). Move only the browser work to a worker.
        if sys.platform == "win32":
            return await asyncio.to_thread(scrape_job_page_in_worker, request.url)
        return await scrape_job_page(request.url)
    except JobScrapeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/match")
def match_resume(request: MatchRequest):
    """A transparent baseline scorer; can be swapped for OpenAI/Gemini server-side."""
    resume_words = extract_keywords(request.resume_text)
    jd_words = extract_keywords(request.job_description)
    overlap = resume_words & jd_words
    score = round(100 * len(overlap) / max(1, len(jd_words)))
    return {"score": min(score, 100), "matched_keywords": sorted(overlap)[:20], "missing_keywords": sorted(jd_words - resume_words)[:20]}
