from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import DailySnapshot, Transaction, User, Watchlist
from ..schemas import PortfolioOut, WatchIn
from ..services import market_data, trading

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioOut)
def portfolio(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return trading.build_portfolio(db, user)


@router.get("/portfolio/transactions")
def transactions(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.timestamp.desc())
        .limit(min(limit, 200))
    ).all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "type": t.type.value,
            "shares": t.shares,
            "price": float(t.price),
            "realized_pnl": float(t.realized_pnl),
            "timestamp": t.timestamp,
        }
        for t in rows
    ]


@router.get("/portfolio/history")
def history(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(DailySnapshot)
        .where(DailySnapshot.user_id == user.id)
        .order_by(DailySnapshot.snapshot_date.desc())
        .limit(min(days, 365))
    ).all()
    return [
        {"date": r.snapshot_date, "net_worth": float(r.net_worth), "daily_return_pct": float(r.daily_return_pct)}
        for r in reversed(rows)
    ]


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    latest = db.scalar(select(DailySnapshot.snapshot_date).order_by(DailySnapshot.snapshot_date.desc()).limit(1))
    if latest is None:
        return []
    rows = db.execute(
        select(DailySnapshot, User)
        .join(User, User.id == DailySnapshot.user_id)
        .where(DailySnapshot.snapshot_date == latest)
        .order_by(DailySnapshot.rank)
        .limit(50)
    ).all()
    return [
        {"rank": s.rank, "display_name": u.display_name, "net_worth": float(s.net_worth), "daily_return_pct": float(s.daily_return_pct)}
        for s, u in rows
    ]


@router.get("/watchlist")
def get_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Watchlist).where(Watchlist.user_id == user.id)).all()
    return [q for w in items if (q := market_data.get_quote(w.symbol))]


@router.post("/watchlist", status_code=201)
def add_watch(body: WatchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    symbol = body.symbol.upper().strip()
    if not market_data.get_quote(symbol):
        raise HTTPException(404, f"Unknown ticker {symbol}")
    exists = db.scalar(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.symbol == symbol))
    if not exists:
        db.add(Watchlist(user_id=user.id, symbol=symbol))
        db.commit()
    return {"symbol": symbol}


@router.delete("/watchlist/{symbol}")
def remove_watch(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.symbol == symbol.upper()))
    if item:
        db.delete(item)
        db.commit()
    return {"removed": symbol.upper()}
