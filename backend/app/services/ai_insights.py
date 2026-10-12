"""AI portfolio analysis via the Anthropic API, with a rule-based fallback so the
feature still works offline / without an API key (important for demos)."""
import json

from ..config import get_settings
from ..schemas import AIAnalysisOut, PortfolioOut

settings = get_settings()


def _heuristic(p: PortfolioOut) -> AIAnalysisOut:
    total = p.net_worth or 1
    cash_pct = p.cash / total * 100
    weights = sorted(((h.market_value / total * 100, h.symbol) for h in p.holdings), reverse=True)
    top_w, top_sym = weights[0] if weights else (0, "-")
    n = len(p.holdings)

    risk = 30
    if top_w > 40:
        risk += 35
    elif top_w > 25:
        risk += 15
    if n < 3 and n > 0:
        risk += 15
    if cash_pct < 5:
        risk += 10
    risk = min(risk, 95)

    tips = []
    if n == 0:
        tips.append("You hold no positions yet - start small in 2-3 sectors to learn how prices move.")
    if top_w > 25:
        tips.append(f"{top_sym} is {top_w:.0f}% of your portfolio; consider trimming to reduce single-stock risk.")
    if n < 5 and n > 0:
        tips.append("Add positions across different sectors to improve diversification.")
    if cash_pct > 60:
        tips.append("Over 60% of your net worth is idle cash; decide whether that is a deliberate choice.")
    if cash_pct < 5 and n > 0:
        tips.append("Keep a small cash buffer so you can act on opportunities.")
    if not tips:
        tips.append("Allocation looks balanced. Keep reviewing position sizes as prices move.")

    div = "Well diversified" if n >= 6 and top_w < 25 else "Moderately concentrated" if n >= 3 else "Highly concentrated"
    return AIAnalysisOut(
        summary=f"Net worth {p.net_worth:,.2f} across {n} position(s); {cash_pct:.0f}% in cash; total return {p.total_return_pct:+.2f}%.",
        risk_score=risk,
        diversification=div,
        suggestions=tips,
        source="rule-based",
    )


def analyze_portfolio(p: PortfolioOut) -> AIAnalysisOut:
    if not settings.anthropic_api_key:
        return _heuristic(p)
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "You are a financial-literacy coach for students using a SIMULATED trading sandbox. "
            "Analyze this virtual portfolio. This is educational, not investment advice. "
            "Reply with ONLY valid JSON: {\"summary\": str, \"risk_score\": int 0-100, "
            "\"diversification\": str, \"suggestions\": [str, ...3-5 items]}.\n\n"
            f"Portfolio JSON:\n{p.model_dump_json()}"
        )
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        return AIAnalysisOut(
            summary=data["summary"],
            risk_score=int(data["risk_score"]),
            diversification=data["diversification"],
            suggestions=list(data["suggestions"]),
            source=f"anthropic:{settings.anthropic_model}",
        )
    except Exception:
        return _heuristic(p)
