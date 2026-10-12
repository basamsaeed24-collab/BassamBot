from typing import Any, TypedDict


class TradingState(TypedDict, total=False):
    symbol: str
    candles: list[dict[str, Any]]
    news: list[dict[str, str]]
    technical: dict[str, Any]
    sentiment: dict[str, Any]
    risk: dict[str, Any]
    execution: dict[str, Any]
    errors: list[str]