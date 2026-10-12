# Trading Multi-Agent

A small Python market-analysis pipeline with technical, headline-sentiment, and risk agents. The execution agent creates a paper-trade proposal only; the app does not connect to a broker or place orders.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `ACCOUNT_EQUITY`, `RISK_PER_TRADE_PCT`, and `MAX_POSITION_PCT` in `.env` to the values you want used for hypothetical sizing. If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are both set, the CLI analysis output is also sent to Telegram after a non-bot run.

## Run an analysis

```powershell
python bot_main.py AAPL
```

Symbols such as `MSFT` and `BTC-USD` are accepted. Market history comes from Yahoo Finance and headlines from Google News RSS; network access is required. The sentiment score is a small keyword heuristic, not a language model.

## Telegram

Set `TELEGRAM_BOT_TOKEN` in `.env`, then run:

```powershell
python bot_main.py --telegram
```

Use `/analyze [SYMBOL]` in Telegram. Omitting the symbol uses `DEFAULT_SYMBOL`.

Analysis output is informational only, can be delayed or incomplete, and is not financial advice. Validate data and risk settings independently before making any investment decisions.