from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Holding, Transaction, TxType, User
from ..schemas import HoldingOut, PortfolioOut
from . import market_data

D = Decimal


def _price(symbol: str) -> D:
    p = market_data.get_price(symbol)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol {symbol}")
    return D(str(p))


def _locked_user(db: Session, user_id: int) -> User:
    # SELECT ... FOR UPDATE serialises concurrent trades by the same user
    # (ignored by SQLite, which serialises writes anyway).
    return db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()


def execute_buy(db: Session, user_id: int, symbol: str, shares: int) -> Transaction:
    symbol = symbol.upper().strip()
    price = _price(symbol)
    cost = price * shares
    user = _locked_user(db, user_id)
    cash = D(str(user.virtual_cash_balance))
    if cost > cash:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient funds: need {cost:.2f}, have {cash:.2f}")

    holding = db.scalar(select(Holding).where(Holding.user_id == user_id, Holding.symbol == symbol))
    if holding:
        old_q, old_avg = holding.quantity, D(str(holding.avg_buy_price))
        new_q = old_q + shares
        holding.avg_buy_price = (old_avg * old_q + cost) / new_q
        holding.quantity = new_q
    else:
        db.add(Holding(user_id=user_id, symbol=symbol, quantity=shares, avg_buy_price=price))

    user.virtual_cash_balance = cash - cost
    tx = Transaction(user_id=user_id, symbol=symbol, type=TxType.BUY, shares=shares, price=price, realized_pnl=0)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def execute_sell(db: Session, user_id: int, symbol: str, shares: int) -> Transaction:
    symbol = symbol.upper().strip()
    price = _price(symbol)
    user = _locked_user(db, user_id)
    holding = db.scalar(
        select(Holding).where(Holding.user_id == user_id, Holding.symbol == symbol).with_for_update()
    )
    if not holding or holding.quantity < shares:
        have = holding.quantity if holding else 0
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot sell {shares} {symbol}: you hold {have}")

    proceeds = price * shares
    realized = (price - D(str(holding.avg_buy_price))) * shares
    holding.quantity -= shares
    if holding.quantity == 0:
        db.delete(holding)
    user.virtual_cash_balance = D(str(user.virtual_cash_balance)) + proceeds
    tx = Transaction(user_id=user_id, symbol=symbol, type=TxType.SELL, shares=shares, price=price, realized_pnl=realized)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def build_portfolio(db: Session, user: User) -> PortfolioOut:
    holdings = db.scalars(select(Holding).where(Holding.user_id == user.id).order_by(Holding.symbol)).all()
    rows: list[HoldingOut] = []
    total = D(0)
    for h in holdings:
        price = _price(h.symbol)
        value = price * h.quantity
        cost = D(str(h.avg_buy_price)) * h.quantity
        pnl = value - cost
        total += value
        rows.append(
            HoldingOut(
                symbol=h.symbol,
                quantity=h.quantity,
                avg_buy_price=float(round(D(str(h.avg_buy_price)), 2)),
                current_price=float(price),
                market_value=float(round(value, 2)),
                unrealized_pnl=float(round(pnl, 2)),
                unrealized_pnl_pct=float(round(pnl / cost * 100, 2)) if cost else 0.0,
            )
        )
    cash = D(str(user.virtual_cash_balance))
    net = cash + total
    from ..config import get_settings

    start = D(str(get_settings().starting_cash))
    return PortfolioOut(
        cash=float(round(cash, 2)),
        holdings_value=float(round(total, 2)),
        net_worth=float(round(net, 2)),
        total_return_pct=float(round((net - start) / start * 100, 2)),
        holdings=rows,
    )
