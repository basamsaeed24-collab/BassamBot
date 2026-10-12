from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _ema(values: Sequence[float], period: int) -> list[float]:
    multiplier = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result


def _sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calculate_indicators(candles: Sequence[dict[str, Any]]) -> dict[str, float | None]:
    if not candles:
        return {"sma_20": None, "sma_50": None, "rsi_14": None, "macd": None, "macd_signal": None, "atr_14": None}

    closes = [float(candle["close"]) for candle in candles]
    gains: list[float] = []
    losses: list[float] = []
    true_ranges: list[float] = []
    for index in range(1, len(candles)):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
        candle = candles[index]
        true_ranges.append(
            max(
                float(candle["high"]) - float(candle["low"]),
                abs(float(candle["high"]) - closes[index - 1]),
                abs(float(candle["low"]) - closes[index - 1]),
            )
        )

    rsi: float | None = None
    if len(gains) >= 14:
        average_gain = sum(gains[-14:]) / 14
        average_loss = sum(losses[-14:]) / 14
        if average_loss == 0:
            rsi = 100.0 if average_gain else 50.0
        else:
            rsi = 100 - (100 / (1 + average_gain / average_loss))

    macd_line: float | None = None
    macd_signal: float | None = None
    if len(closes) >= 26:
        fast = _ema(closes, 12)
        slow = _ema(closes, 26)
        macd_values = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
        macd_line = macd_values[-1]
        macd_signal = _ema(macd_values, 9)[-1]

    return {
        "sma_20": _sma(closes, 20),
        "sma_50": _sma(closes, 50),
        "rsi_14": rsi,
        "macd": macd_line,
        "macd_signal": macd_signal,
        "atr_14": sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else None,
    }