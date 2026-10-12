from __future__ import annotations

import os
from html import escape
from typing import Any

import requests


def send_telegram_message(text: str, reply_markup=None) -> dict[str, Any] | None:
    token = os.getenv("https://api.telegram.org/bot8724101765:AAHJzYCNIPmivtAcOGMMbS_ECsL7PmWAdlg/sendMessage", "").strip()
    chat_id = os.getenv("1039136464", "").strip()
    if not token or not chat_id:
        return None

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": escape(text),
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Telegram send failed: {exc}")
        return None


def _price(value: Any) -> str:
    return f"${value:,.2f}" if isinstance(value, (int, float)) else "n/a"


def _number(value: Any) -> str:
    return f"{value:.1f}" if isinstance(value, (int, float)) else "n/a"


def format_analysis(state: dict[str, Any]) -> str:
    symbol = state.get("symbol", "Unknown")
    technical = state.get("technical", {})
    sentiment = state.get("sentiment", {})
    risk = state.get("risk", {})
    execution = state.get("execution", {})
    indicators = technical.get("indicators", {})

    lines = [
        f"{symbol} analysis",
        f"Price: {_price(technical.get('price'))}",
        f"Technical signal: {technical.get('signal', 'UNKNOWN')}",
        technical.get("rationale", "No technical analysis available."),
        f"RSI 14: {_number(indicators.get('rsi_14'))}",
        f"News sentiment: {sentiment.get('label', 'UNKNOWN')} ({sentiment.get('score', 0.0):+.2f})",
    ]

    if execution.get("status") == "PAPER_PROPOSAL":
        lines.extend(
            [
                f"Paper proposal: BUY {execution['quantity']} shares",
                f"Entry: {_price(execution['entry_price'])} | Stop: {_price(execution['stop_price'])}",
                "No order was sent to a broker or exchange.",
            ]
        )
    else:
        reasons = risk.get("blocked_reasons", [])
        lines.append("Paper proposal: none" + (f" ({'; '.join(reasons)})" if reasons else ""))

    headlines = state.get("news", [])
    if headlines:
        lines.append("Recent headlines:")
        lines.extend(f"- {item['title']}" for item in headlines[:3])
    for error in state.get("errors", []):
        lines.append(f"Data note: {error}")

    lines.append("Research output only; not financial advice.")
    return "\n".join(lines)