from __future__ import annotations

import os
import re

from agents.execution import create_paper_proposal
from agents.risk import assess_risk
from agents.sentiment import analyze_sentiment
from agents.technical import analyze_technicals
from state import TradingState
from tools.market_data import fetch_candles
from tools.news import fetch_news


def _setting(name: str, default: str, cast: type[float] | type[int]) -> float | int:
    raw_value = os.getenv(name, default)
    try:
        return cast(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a valid {cast.__name__}.") from error


def analyze_symbol(
    symbol: str,
    *,
    period: str | None = None,
    account_equity: float | None = None,
    risk_per_trade_pct: float | None = None,
    max_position_pct: float | None = None,
    news_limit: int | None = None,
) -> TradingState:
    normalized_symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.^=-]{1,20}", normalized_symbol):
        raise ValueError("Enter a valid ticker symbol, such as AAPL or BTC-USD.")

    state: TradingState = {"symbol": normalized_symbol, "candles": [], "news": [], "errors": []}
    try:
        state["candles"] = fetch_candles(normalized_symbol, period or os.getenv("MARKET_PERIOD", "6mo"))
    except Exception as error:
        state["errors"].append(f"Market data unavailable: {error}")

    resolved_news_limit = news_limit if news_limit is not None else int(_setting("NEWS_LIMIT", "8", int))
    try:
        state["news"] = fetch_news(normalized_symbol, resolved_news_limit)
    except Exception as error:
        state["errors"].append(f"News unavailable: {error}")

    state["technical"] = analyze_technicals(state["candles"])
    state["sentiment"] = analyze_sentiment(state["news"])
    equity = account_equity if account_equity is not None else float(_setting("ACCOUNT_EQUITY", "10000", float))
    risk_pct = risk_per_trade_pct if risk_per_trade_pct is not None else float(
        _setting("RISK_PER_TRADE_PCT", "1", float)
    )
    position_pct = max_position_pct if max_position_pct is not None else float(
        _setting("MAX_POSITION_PCT", "20", float)
    )
    state["risk"] = assess_risk(state["technical"], state["sentiment"], equity, risk_pct, position_pct)
    state["execution"] = create_paper_proposal(state["risk"])
    return state