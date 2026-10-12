"""Domain agents for market analysis and paper-trade decisions."""

from .execution import create_paper_proposal
from .risk import assess_risk
from .sentiment import analyze_sentiment
from .technical import analyze_technicals

__all__ = [
    "analyze_sentiment",
    "analyze_technicals",
    "assess_risk",
    "create_paper_proposal",
]
