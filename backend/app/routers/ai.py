from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import AIAnalysisOut
from ..services import ai_insights, trading

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/analyze-portfolio", response_model=AIAnalysisOut)
def analyze(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    portfolio = trading.build_portfolio(db, user)
    return ai_insights.analyze_portfolio(portfolio)
