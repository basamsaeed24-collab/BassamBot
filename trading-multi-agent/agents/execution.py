from __future__ import annotations

from typing import Any


def create_paper_proposal(risk: dict[str, Any]) -> dict[str, Any]:
    if not risk.get("approved"):
        return {"status": "NOT_PROPOSED", "message": "Risk checks did not approve a paper-trade proposal."}

    return {
        "status": "PAPER_PROPOSAL",
        "side": "BUY",
        "quantity": risk["quantity"],
        "entry_price": risk["entry_price"],
        "stop_price": risk["stop_price"],
        "position_value": risk["position_value"],
        "message": "Proposal only. No order was sent to a broker or exchange.",
    }