"""PDF generation with ReportLab: weekly statement + trade confirmation slip."""
import io
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from ..models import DailySnapshot, Transaction, User  # noqa: E402
from . import trading  # noqa: E402

GREEN = colors.HexColor("#0f9d58")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    t.setStyle(TableStyle(style))
    return t


def _networth_chart(points: list[tuple[str, float]]) -> io.BytesIO | None:
    if len(points) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 2.6), dpi=150)
    ax.plot([p[0] for p in points], [p[1] for p in points], color="#0f9d58", linewidth=2)
    ax.fill_between(range(len(points)), [p[1] for p in points], min(p[1] for p in points), alpha=0.12, color="#0f9d58")
    ax.set_title("Net worth - last 7 snapshots", fontsize=9, loc="left")
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def weekly_statement_pdf(db: Session, user: User) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    p = trading.build_portfolio(db, user)

    story = [
        Paragraph("<b>NeoMint</b> - Weekly Portfolio Performance Statement", styles["Title"]),
        Paragraph(f"{user.display_name} &middot; {user.email}<br/>Period: {week_ago:%d %b %Y} to {now:%d %b %Y}", styles["Normal"]),
        Spacer(1, 8),
        _table(
            [
                ["Cash", "Holdings value", "Net worth", "Total return"],
                [f"{p.cash:,.2f}", f"{p.holdings_value:,.2f}", f"{p.net_worth:,.2f}", f"{p.total_return_pct:+.2f}%"],
            ]
        ),
        Spacer(1, 10),
    ]

    snaps = db.scalars(
        select(DailySnapshot).where(DailySnapshot.user_id == user.id).order_by(DailySnapshot.snapshot_date.desc()).limit(7)
    ).all()
    chart = _networth_chart([(s.snapshot_date.strftime("%d %b"), float(s.net_worth)) for s in reversed(snaps)])
    if chart:
        story += [Image(chart, width=170 * mm, height=63 * mm), Spacer(1, 8)]

    story.append(Paragraph("Current holdings", styles["Heading3"]))
    rows = [["Symbol", "Qty", "Avg cost", "Price", "Value", "P&L", "P&L %"]]
    for h in p.holdings:
        rows.append([h.symbol, h.quantity, f"{h.avg_buy_price:,.2f}", f"{h.current_price:,.2f}", f"{h.market_value:,.2f}", f"{h.unrealized_pnl:+,.2f}", f"{h.unrealized_pnl_pct:+.2f}%"])
    if len(rows) == 1:
        rows.append(["No open positions", "", "", "", "", "", ""])
    story += [_table(rows), Spacer(1, 10), Paragraph("Transactions this week", styles["Heading3"])]

    txs = db.scalars(
        select(Transaction).where(Transaction.user_id == user.id, Transaction.timestamp >= week_ago).order_by(Transaction.timestamp)
    ).all()
    trows = [["Date", "Type", "Symbol", "Shares", "Price", "Total", "Realized P&L"]]
    for t in txs:
        trows.append([t.timestamp.strftime("%d %b %H:%M"), t.type.value, t.symbol, t.shares, f"{float(t.price):,.2f}", f"{float(t.price) * t.shares:,.2f}", f"{float(t.realized_pnl):+,.2f}"])
    if len(trows) == 1:
        trows.append(["No trades this week", "", "", "", "", "", ""])
    story += [_table(trows), Spacer(1, 14), Paragraph("<font color='#6b7280' size=7>Simulated trading for educational purposes only. Not investment advice.</font>", styles["Normal"])]

    doc.build(story)
    return buf.getvalue()


def trade_slip_pdf(tx: Transaction, user: User) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(110 * mm, 150 * mm), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
    total = float(tx.price) * tx.shares
    story = [
        Paragraph("<b>NeoMint</b> Trade Confirmation", styles["Heading2"]),
        Paragraph(f"Slip #{tx.id:07d}", styles["Normal"]),
        Spacer(1, 6),
        _table(
            [
                ["Account", user.email],
                ["Executed", tx.timestamp.strftime("%d %b %Y %H:%M:%S UTC")],
                ["Action", tx.type.value],
                ["Symbol", tx.symbol],
                ["Shares", str(tx.shares)],
                ["Price", f"{float(tx.price):,.2f}"],
                ["Total", f"{total:,.2f}"],
                ["Realized P&L", f"{float(tx.realized_pnl):+,.2f}"],
            ],
            col_widths=[30 * mm, 60 * mm],
            header=False,
        ),
        Spacer(1, 10),
        Paragraph("<font color='#6b7280' size=7>Virtual funds. Educational simulation only.</font>", styles["Normal"]),
    ]
    doc.build(story)
    return buf.getvalue()
