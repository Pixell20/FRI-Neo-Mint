# NeoMint

Gamified financial-literacy and simulated trading sandbox (internship capstone).
Students trade with virtual cash, climb a nightly leaderboard, get AI feedback, and download PDF statements.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), React, Tailwind CSS, Lucide, Recharts |
| Backend | FastAPI (Python 3.12) |
| DB / ORM | PostgreSQL 16, SQLAlchemy 2 |
| Cache | Redis (quote cache, in-memory fallback if Redis is down) |
| Jobs | APScheduler (cron) running inside the API process |
| PDF | ReportLab + matplotlib charts |
| AI | Anthropic API (rule-based fallback when no key is set) |

## Run it

```bash
docker compose up --build
# web: http://localhost:3000   api docs: http://localhost:8000/docs
```

Without Docker:

```bash
cd backend && pip install -r requirements.txt
cp .env.example .env            # set DATABASE_URL, JWT_SECRET, optionally ANTHROPIC_API_KEY
uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

An admin account is seeded on startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD` (change these!).
Run the tests: `cd backend && python -m pytest -q tests`.

## Capstone requirement mapping

1. **Authentication** - `app/security.py` (Argon2id hashing, JWT HS256 with expiry), `app/deps.py` (`get_current_user`, `require_admin`), `app/routers/auth.py`. Self-registration always creates a `STUDENT`; admins are seeded. Frontend routes are gated by `middleware.ts` and the API verifies the JWT on every call.
2. **API endpoints** - `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/trade/buy`, `POST /api/trade/sell`, `GET /api/portfolio`, `GET /api/market/stocks`, `GET /api/market/quote/{ticker}`, `POST /api/ai/analyze-portfolio`, plus transactions, history, leaderboard, watchlist, reports and an admin trigger. Interactive docs at `/docs`.
3. **Database** - `app/models.py`: `users`, `holdings`, `transactions`, `watchlists`, `daily_snapshots` with FKs, unique constraints (one holding per user+symbol, one snapshot per user+day) and indexes. Money columns use `NUMERIC(18,4)` and Decimal math.
4. **Cron job** - `app/jobs/scheduler.py`: `nightly_close` runs daily (default 18:00 UTC), marks every student portfolio to market, upserts a `DailySnapshot`, computes daily return, assigns leaderboard ranks, and resets the daily counter. It is idempotent per date. Admins can trigger it at `POST /api/admin/run-nightly-close`.
5. **Reporting** - `app/services/pdf_reports.py`: weekly performance statement (summary, net-worth chart, holdings, week's transactions) at `GET /api/reports/weekly-statement`, and a per-trade confirmation slip at `GET /api/reports/trade-slip/{id}` (owner only).
6. **Bonus: Redis caching** - `app/services/market_data.py` caches quotes for `QUOTE_CACHE_SECONDS` (default 15).

## Design notes and honest limitations

- **Market data is simulated** (seeded random walk) so the app works offline and is reproducible. To use real prices, replace `get_quote` in `market_data.py` with a provider call (e.g. Alpha Vantage or yfinance) and keep the cache layer.
- **Trade integrity**: each trade runs in one DB transaction with `SELECT ... FOR UPDATE` on the user row, so concurrent requests cannot overspend. Verified paths: insufficient funds, overselling, unknown symbol.
- **Scheduler**: APScheduler inside the API process is fine for a single instance. If you run several API replicas, run the scheduler in one dedicated worker (set `ENABLE_SCHEDULER=false` on the others) or move the job to Celery beat / BullMQ.
- **Schema migrations**: tables are created with `create_all` at startup for convenience; add Alembic before real deployment.
- **Frontend session**: the JWT is kept in `localStorage` and a non-sensitive presence cookie drives route gating. For production, prefer an httpOnly cookie set by the API.
- **Email dispatch** is not implemented. PDFs are generated on demand and downloadable. Adding SMTP (e.g. `smtplib` or SendGrid) to the nightly job to attach the weekly statement is the natural next step.
- Shadcn UI / Tremor were not added; the UI uses Tailwind utility components and Recharts to keep setup light.
- Educational simulation only; nothing here is investment advice.
