import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import get_settings
from .database import Base, SessionLocal, engine
from .deps import require_admin
from .jobs.scheduler import nightly_close, start_scheduler
from .models import Role, User
from .routers import ai, auth, market, portfolio, reports, trade
from .security import hash_password

logging.basicConfig(level=logging.INFO)
settings = get_settings()


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        if not db.scalar(select(User).where(User.email == settings.admin_email)):
            db.add(
                User(
                    email=settings.admin_email,
                    display_name="Admin",
                    password_hash=hash_password(settings.admin_password),
                    role=Role.ADMIN,
                    virtual_cash_balance=0,
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # use Alembic migrations for production
    _seed_admin()
    sched = start_scheduler() if settings.enable_scheduler else None
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="NeoMint API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, market, trade, portfolio, ai, reports):
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/admin/run-nightly-close", tags=["admin"])
def run_nightly(_: User = Depends(require_admin)):
    """Admin-only manual trigger of the nightly cron job (useful for demos)."""
    return {"snapshots": nightly_close()}
