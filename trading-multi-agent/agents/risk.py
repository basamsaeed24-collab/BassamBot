from __future__ import annotations

from typing import Any


def assess_risk(
    technical: dict[str, Any],
    sentiment: dict[str, Any],
    account_equity: float,
    risk_per_trade_pct: float,
    max_position_pct: float,
) -> dict[str, Any]:
    signal = technical.get("signal", "HOLD")
    price = technical.get("price")
    atr = technical.get("indicators", {}).get("atr_14")
    sentiment_score = float(sentiment.get("score", 0.0))
    blocked_reasons: list[str] = []

    if signal != "BUY":
        blocked_reasons.append("Only aligned BUY signals are eligible for a paper-trade proposal.")
    if sentiment_score < -0.25:
        blocked_reasons.append("Negative headline sentiment blocks the proposal.")
    if not isinstance(price, (int, float)) or price <= 0:
        blocked_reasons.append("A valid market price is required.")
    if account_equity <= 0 or risk_per_trade_pct <= 0 or max_position_pct <= 0:
        blocked_reasons.append("Risk settings and account equity must be positive.")

    if blocked_reasons:
        return {"approved": False, "quantity": 0, "blocked_reasons": blocked_reasons}

    stop_distance = float(atr) * 2 if isinstance(atr, (int, float)) and atr > 0 else float(price) * 0.03
    risk_budget = account_equity * risk_per_trade_pct / 100
    position_cap = account_equity * max_position_pct / 100
    quantity = max(0, int(min(risk_budget / stop_distance, position_cap / float(price))))
    if quantity < 1:
        blocked_reasons.append("Position sizing rounded below one share under the configured limits.")

    return {
        "approved": quantity > 0,
        "quantity": quantity,
        "entry_price": float(price),
        "stop_price": max(0.0, float(price) - stop_distance),
        "risk_budget": risk_budget,
        "position_value": quantity * float(price),
        "blocked_reasons": blocked_reasons,
    }