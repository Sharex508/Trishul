from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from .binance_client import BinanceClient


def compute_imbalance(bids: list[list[float]], asks: list[list[float]]) -> float:
    bid_vol = sum(q for _, q in bids)
    ask_vol = sum(q for _, q in asks)
    denom = bid_vol + ask_vol
    return (bid_vol - ask_vol) / denom if denom > 0 else 0.0


async def ingest_orderbook_snapshot(
    session: AsyncSession,
    symbol: str,
    client: Optional[BinanceClient] = None,
    levels: int = 20,
    depth_data: Optional[dict] = None,
) -> Optional[models.OrderbookSnapshot]:
    """Grab a single orderbook snapshot (WS preferred, REST fallback) and persist."""
    client = client or BinanceClient()
    data = depth_data
    if data is None:
        data = await client.get_orderbook(symbol, limit=levels)
    bids = [[float(p), float(q)] for p, q in (data.get("bids") or [])[:levels]]
    asks = [[float(p), float(q)] for p, q in (data.get("asks") or [])[:levels]]
    if not bids and not asks:
        return None
    spread = 0.0
    if bids and asks:
        spread = max(0.0, asks[0][0] - bids[0][0])
    ts_ms = data.get("event_time") or data.get("T")
    ts = datetime.now(timezone.utc).replace(tzinfo=None) if ts_ms is None else datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).replace(tzinfo=None)

    ob = models.OrderbookSnapshot(
        symbol=symbol.upper(),
        bids=bids,
        asks=asks,
        imbalance=compute_imbalance(bids, asks),
        spread=spread,
        ts=ts,
    )
    session.add(ob)
    await session.commit()
    await session.refresh(ob)
    return ob


async def stream_orderbook_to_db(session: AsyncSession, symbol: str, client: Optional[BinanceClient] = None, levels: int = 20):
    """Continuously stream depth over WS and write snapshots; reconnects on disconnect."""
    client = client or BinanceClient()
    while True:
        try:
            async for depth in client.stream_depth(symbol, levels=levels):
                await ingest_orderbook_snapshot(session, symbol, client=client, levels=levels, depth_data=depth)
        except Exception:
            await asyncio.sleep(1.0)
