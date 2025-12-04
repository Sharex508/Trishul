from __future__ import annotations
from fastapi import APIRouter, Query
from src.schemas import IntentionOut
from src.ai_agent.agent import next_intention

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/intents/next", response_model=IntentionOut)
async def get_next_intention(symbol: str = Query(..., description="Trading symbol, e.g., BTCUSDT"), lot_size: float = 0.001):
    intent = await next_intention(symbol.upper(), lot_size=lot_size)
    return IntentionOut(
        symbol=intent.symbol,
        action=intent.action,
        size=intent.size,
        confidence=intent.confidence,
        explanation=intent.explanation,
    )
