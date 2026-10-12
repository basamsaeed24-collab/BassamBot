from __future__ import annotations

from typing import Any

from tools.indicators import calculate_indicators


def analyze_technicals(candles: list[dict[str, Any]]) -> dict[str, Any]:
    indicators = calculate_indicators(candles)
    price = float(candles[-1]["close"]) if candles else None
    sma_20 = indicators["sma_20"]
    sma_50 = indicators["sma_50"]
    rsi = indicators["rsi_14"]
    macd = indicators["macd"]
    macd_signal = indicators["macd_signal"]

    if price is None or sma_20 is None or sma_50 is None or rsi is None or macd is None or macd_signal is None:
        signal = "HOLD"
        rationale = "Insufficient history to evaluate all indicators."
    elif price > sma_20 > sma_50 and 45 <= rsi <= 70 and macd > macd_signal:
        signal = "BUY"
        rationale = "Price and moving averages trend upward; RSI and MACD confirm momentum."
    elif price < sma_20 < sma_50 and rsi < 55 and macd < macd_signal:
        signal = "SELL"
        rationale = "Price and moving averages trend downward; RSI and MACD confirm weakness."
    else:
        signal = "HOLD"
        rationale = "Trend and momentum indicators do not align."

    return {
        "signal": signal,
        "price": price,
        "indicators": indicators,
        "rationale": rationale,
    }