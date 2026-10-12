"""Background jobs (APScheduler).

nightly_close: mark every portfolio to market, store a DailySnapshot, rank users
into the daily leaderboard, and reset per-day counters.
"""
import logging
from datetime import date
from decimal import Decimal

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from ..config import get_settings
from ..database import SessionLocal
from ..models import DailySnapshot, Role, User
from ..services import trading

log = logging.getLogger("neomint.jobs")
settings = get_settings()


def nightly_close(snapshot_date: date | None = None) -> int:
    """Idempotent: re-running for the same date updates rather than duplicates."""
    snapshot_date = snapshot_date or date.today()
    db = SessionLocal()
    try:
        users = db.scalars(select(User).where(User.role == Role.STUDENT)).all()
        rows: list[DailySnapshot] = []
        for u in users:
            p = trading.build_portfolio(db, u)
            prev = db.scalar(
                select(DailySnapshot)
                .where(DailySnapshot.user_id == u.id, DailySnapshot.snapshot_date < snapshot_date)
                .order_by(DailySnapshot.snapshot_date.desc())
                .limit(1)
            )
            prev_nw = Decimal(str(prev.net_worth)) if prev else Decimal(str(settings.starting_cash))
            nw = Decimal(str(p.net_worth))
            ret = ((nw - prev_nw) / prev_nw * 100) if prev_nw else Decimal(0)

            snap = db.scalar(
                select(DailySnapshot).where(DailySnapshot.user_id == u.id, DailySnapshot.snapshot_date == snapshot_date)
            )
            if snap is None:
                snap = DailySnapshot(user_id=u.id, snapshot_date=snapshot_date)
                db.add(snap)
            snap.cash = p.cash
            snap.holdings_value = p.holdings_value
            snap.net_worth = p.net_worth
            snap.daily_return_pct = round(ret, 4)
            u.daily_pnl_pct = 0  # reset daily leaderboard counter for the new day
            rows.append(snap)

        rows.sort(key=lambda s: float(s.net_worth), reverse=True)
        for i, s in enumerate(rows, start=1):
            s.rank = i
        db.commit()
        log.info("nightly_close: %d snapshots recorded for %s", len(rows), snapshot_date)
        return len(rows)
    except Exception:
        db.rollback()
        log.exception("nightly_close failed")
        raise
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(
        nightly_close,
        "cron",
        hour=settings.nightly_hour_utc,
        minute=settings.nightly_minute_utc,
        id="nightly_close",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    sched.start()
    log.info("Scheduler started; nightly_close at %02d:%02d UTC", settings.nightly_hour_utc, settings.nightly_minute_utc)
    return sched
