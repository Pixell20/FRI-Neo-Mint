from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Transaction, User
from ..schemas import TradeIn, TradeOut
from ..services import trading

router = APIRouter(prefix="/api/trade", tags=["trade"])


def _out(tx: Transaction, user: User) -> TradeOut:
    return TradeOut(
        transaction_id=tx.id,
        symbol=tx.symbol,
        type=tx.type.value,
        shares=tx.shares,
        price=float(tx.price),
        total=float(round(float(tx.price) * tx.shares, 2)),
        realized_pnl=float(round(float(tx.realized_pnl), 2)),
        cash_balance=float(round(float(user.virtual_cash_balance), 2)),
    )


@router.post("/buy", response_model=TradeOut)
def buy(body: TradeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = trading.execute_buy(db, user.id, body.symbol, body.shares)
    db.refresh(user)
    return _out(tx, user)


@router.post("/sell", response_model=TradeOut)
def sell(body: TradeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = trading.execute_sell(db, user.id, body.symbol, body.shares)
    db.refresh(user)
    return _out(tx, user)
