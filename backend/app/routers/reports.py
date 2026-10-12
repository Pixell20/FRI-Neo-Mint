from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Transaction, User
from ..services import pdf_reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/weekly-statement")
def weekly_statement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pdf = pdf_reports.weekly_statement_pdf(db, user)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="neomint-weekly-statement.pdf"'})


@router.get("/trade-slip/{tx_id}")
def trade_slip(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx or tx.user_id != user.id:  # users can only fetch their own slips
        raise HTTPException(404, "Transaction not found")
    pdf = pdf_reports.trade_slip_pdf(tx, user)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="trade-slip-{tx.id}.pdf"'})
