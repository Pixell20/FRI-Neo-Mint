from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user
from ..models import User
from ..schemas import QuoteOut
from ..services import market_data

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/stocks", response_model=list[QuoteOut])
def stocks(_: User = Depends(get_current_user)):
    return market_data.list_stocks()


@router.get("/quote/{ticker}", response_model=QuoteOut)
def quote(ticker: str, _: User = Depends(get_current_user)):
    q = market_data.get_quote(ticker)
    if not q:
        raise HTTPException(404, f"Unknown ticker {ticker.upper()}")
    return q
