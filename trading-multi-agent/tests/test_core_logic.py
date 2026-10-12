import unittest

from agents.risk import assess_risk
from agents.sentiment import analyze_sentiment
from telegram_helper import format_analysis


class CoreLogicTests(unittest.TestCase):
    def test_analyze_sentiment_uses_positive_headlines(self):
        result = analyze_sentiment([{"title": "Strong earnings beat and record gains"}])
        self.assertGreater(result["score"], 0.0)
        self.assertEqual(result["label"], "POSITIVE")

    def test_assess_risk_allows_buy_signal(self):
        technical = {"signal": "BUY", "price": 100.0, "indicators": {"atr_14": 4.0}}
        sentiment = {"score": 0.2}

        result = assess_risk(technical, sentiment, account_equity=10000, risk_per_trade_pct=1, max_position_pct=20)

        self.assertTrue(result["approved"])
        self.assertGreater(result["quantity"], 0)
        self.assertEqual(result["entry_price"], 100.0)

    def test_format_analysis_lists_paper_trade_details(self):
        state = {
            "symbol": "AAPL",
            "technical": {
                "signal": "BUY",
                "price": 100.0,
                "rationale": "Bullish trend.",
                "indicators": {"rsi_14": 62.0},
            },
            "sentiment": {"label": "POSITIVE", "score": 0.5},
            "risk": {"blocked_reasons": []},
            "execution": {"status": "PAPER_PROPOSAL", "quantity": 3, "entry_price": 100.0, "stop_price": 96.0},
            "news": [{"title": "Apple reports record quarter"}],
            "errors": [],
        }

        output = format_analysis(state)

        self.assertIn("AAPL analysis", output)
        self.assertIn("Paper proposal: BUY 3 shares", output)
        self.assertIn("Research output only; not financial advice.", output)


if __name__ == "__main__":
    unittest.main()
