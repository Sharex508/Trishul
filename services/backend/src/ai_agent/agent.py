from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from math import isfinite

from src import crud


@dataclass
class Intention:
    symbol: str
    action: str  # BUY/SELL/HOLD
    size: float
    confidence: float
    explanation: str


def _pct(a: float, b: float) -> float:
    if not (isfinite(a) and isfinite(b)) or b == 0:
        return 0.0
    return (a - b) / b


async def next_intention(symbol: str, lot_size: float = 0.001) -> Intention:
    """
    Simple rules-based agent:
    - Fetch recent prices (last 30).
    - Compare last price to SMA(10) and SMA(30).
    - If price > SMA10 > SMA30 → BUY; if price < SMA10 < SMA30 → SELL; else HOLD.
    - Confidence is proportional to max(abs(price-SMA10)/SMA10, abs(SMA10-SMA30)/SMA30), capped to [0.05, 0.95].
    - Writes an AI log via CRUD and returns an intention.
    """
    symbol = symbol.upper()
    rows = await crud.get_recent_prices(symbol, limit=30)
    if not rows:
        # No data yet → HOLD, low confidence
        await crud.add_ai_log(symbol, "HOLD", 0.1, "No recent prices; holding")
        return Intention(symbol, "HOLD", 0.0, 0.1, "No recent prices")

    prices = [r.price for r in reversed(rows)]  # oldest→newest
    last = prices[-1]
    sma10 = sum(prices[-10:]) / min(len(prices), 10)
    sma30 = sum(prices) / len(prices)

    up_trend = last > sma10 and sma10 >= sma30
    down_trend = last < sma10 and sma10 <= sma30

    a = abs(_pct(last, sma10))
    b = abs(_pct(sma10, sma30))
    conf = max(0.05, min(0.95, (a + b) / 2.0))

    if up_trend and (a > 0.001 or b > 0.001):
        action = "BUY"
        size = lot_size
        rationale = f"Uptrend: price>{'SMA10'}>{'SMA30'}; a={a:.4f}, b={b:.4f}"
    elif down_trend and (a > 0.001 or b > 0.001):
        action = "SELL"
        size = lot_size
        rationale = f"Downtrend: price<{'SMA10'}<{'SMA30'}; a={a:.4f}, b={b:.4f}"
    else:
        action = "HOLD"
        size = 0.0
        rationale = f"No strong trend; a={a:.4f}, b={b:.4f}"

    await crud.add_ai_log(symbol, action, conf, rationale)
    return Intention(symbol, action, size, conf, rationale)
