from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src import models
from .binance_client import BinanceClient


def kline_to_candle(symbol: str, timeframe: str, kline: dict) -> models.Candle:
    ts = datetime.fromtimestamp(kline["open_time"] / 1000, tz=timezone.utc).replace(tzinfo=None)
    return models.Candle(
        symbol=symbol.upper(),
        timeframe=timeframe,
        open=kline["open"],
        high=kline["high"],
        low=kline["low"],
        close=kline["close"],
        volume=kline["volume"],
        ts=ts,
    )


async def ingest_candles(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    lookback: int = 200,
    client: Optional[BinanceClient] = None,
) -> int:
    """Fetch latest candles for symbol/timeframe and upsert in bulk."""
    client = client or BinanceClient()
    klines = await client.get_klines(symbol, timeframe, limit=lookback)
    rows = [kline_to_candle(symbol, timeframe, k) for k in klines]
    if not rows:
        return 0

    payload = [
        {
            "symbol": r.symbol,
            "timeframe": r.timeframe,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "ts": r.ts,
        }
        for r in rows
    ]
    stmt = insert(models.Candle).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "timeframe", "ts"],
        set_={
            "open": stmt.excluded.open,  # type: ignore[attr-defined]
            "high": stmt.excluded.high,  # type: ignore[attr-defined]
            "low": stmt.excluded.low,  # type: ignore[attr-defined]
            "close": stmt.excluded.close,  # type: ignore[attr-defined]
            "volume": stmt.excluded.volume,  # type: ignore[attr-defined]
        },
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount or len(rows)
