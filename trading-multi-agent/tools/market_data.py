from __future__ import annotations

import math

import yfinance as yf


def fetch_candles(symbol: str, period: str = "6mo") -> list[dict[str, float | str]]:
    history = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    if history.empty:
        raise ValueError(f"No market data returned for {symbol}.")

    candles: list[dict[str, float | str]] = []
    for timestamp, row in history.iterrows():
        values = {
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        }
        if not all(math.isfinite(value) for value in values.values()):
            continue
        candles.append({"date": timestamp.date().isoformat(), **values})

    if not candles:
        raise ValueError(f"Market data for {symbol} contains no usable candles.")
    return candles