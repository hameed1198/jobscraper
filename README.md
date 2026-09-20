# JobScraper

A modern job discovery experience: search roles by title, skills, location, work mode and freshness; save the best opportunities; and score a job description against a resume.

## Run locally

```powershell
# terminal 1
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

The UI works immediately in demo mode. Set `VITE_API_URL` to an API URL if it is not `http://localhost:8000`.

Default local login credentials are `hameed@example.com` / `jobscout2026`. Override them on the backend with `JOBSCOUT_USER_EMAIL`, `JOBSCOUT_USER_PASSWORD`, `JOBSCOUT_USER_NAME`, `JOBSCOUT_USER_INITIALS`, and `JOBSCOUT_AUTH_SECRET`.

## Production data sources

`backend/app/providers.py` contains the provider contract. The included API returns demonstrative results so the UI is usable without credentials. Add source-specific adapters only where their terms, robots policy, and rate limits permit automated access. Prefer public job-board APIs, RSS feeds, and company career pages.

For AI-assisted matching, set either `OPENAI_API_KEY` or `GEMINI_API_KEY` on the FastAPI service and replace the deterministic scorer in `app/main.py` with the relevant provider call. Do not expose those keys to the browser.

## Live career-page extraction

The FastAPI backend now includes `POST /api/jobs/scrape-page`. It uses Crawl4AI's async browser, dynamic-page scrolling, boilerplate pruning, and gpt-4o-mini schema extraction. It only accepts public `http(s)` URLs and honours `robots.txt`.

```powershell
cd backend
Copy-Item .env.example .env
# Edit .env and add your real OPENAI_API_KEY
pip install -r requirements.txt
crawl4ai-setup
uvicorn app.main:app --reload --port 8000
```

Test a public career page from another terminal:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/jobs/scrape-page `
  -ContentType "application/json" `
  -Body '{"url":"https://job-boards.greenhouse.io/public"}'
```

You can also invoke the reusable scraper directly:

```powershell
python -m app.job_scraper "https://job-boards.greenhouse.io/public"
```

Only crawl sources whose terms and robots policy permit automated collection. The OpenAI key must remain on the backend; it is read from `backend/.env`, never from the browser.

Workday company-name scraping is available through the search endpoint but disabled by default because guessed Workday portals are often slow or blocked by anti-bot controls. To opt in locally, set `JOBSCOUT_ENABLE_WORKDAY_SCRAPE=true`, keep `OPENAI_API_KEY` configured, and optionally limit probes with `JOBSCOUT_WORKDAY_MAX_CANDIDATES`.
