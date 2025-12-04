from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import websockets
from sqlalchemy import DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------
DB_DSN = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER','crypto')}:{os.getenv('POSTGRES_PASSWORD','crypto')}"
    f"@{os.getenv('POSTGRES_HOST','db')}:{int(os.getenv('POSTGRES_PORT','5432'))}/{os.getenv('POSTGRES_DB','crypto')}"
)
SYMBOLS: List[str] = [s.strip().upper() for s in os.getenv("PRICE_SYMBOLS", "BTCUSDT,ETHUSDT").split(",") if s.strip()]
TIMEFRAMES: List[str] = [tf.strip() for tf in os.getenv("WORKER_TIMEFRAMES", "1m,5m,15m,1h,1d").split(",") if tf.strip()]
CANDLE_INTERVAL_SEC = float(os.getenv("CANDLE_POLL_SEC", "60"))
ORDERBOOK_INTERVAL_SEC = float(os.getenv("ORDERBOOK_SNAPSHOT_SEC", "2"))
CANDLE_LOOKBACK = int(os.getenv("CANDLE_LOOKBACK", "200"))
ORDERBOOK_LEVELS = int(os.getenv("ORDERBOOK_LEVELS", "20"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

# ---------------------------------------------------------------------
# DB models (reflections aligned with backend)
# ---------------------------------------------------------------------
Base = declarative_base()


class Symbol(Base):
    __tablename__ = "symbols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)


class Candle(Base):
    __tablename__ = "candles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)

    __table_args__ = (UniqueConstraint("symbol", "timeframe", "ts", name="uq_candle_symbol_tf_ts"),)


class OrderbookSnapshot(Base):
    __tablename__ = "orderbook_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    bids: Mapped[list] = mapped_column("bids_json", JSON, default=list)
    asks: Mapped[list] = mapped_column("asks_json", JSON, default=list)
    imbalance: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)


class Feature(Base):
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    feature_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)

    __table_args__ = (UniqueConstraint("symbol", "timeframe", "ts", name="uq_feature_symbol_tf_ts"),)


engine = create_async_engine(DB_DSN, echo=False, future=True)
Session: async_sessionmaker[AsyncSession] = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------
# Binance client
# ---------------------------------------------------------------------
class BinanceClient:
    """Minimal REST/WS client with reconnection/backoff."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, base_url: str = "https://api.binance.com"):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_SECRET")
        self.base_url = base_url.rstrip("/")
        self.timeout = float(os.getenv("BINANCE_HTTP_TIMEOUT", "10"))

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        return headers

    async def get_klines(
        self, symbol: str, interval: str, limit: int = 200, start_time: Optional[int] = None, end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"symbol": symbol.upper(), "interval": interval, "limit": min(limit, 1000)}
        if start_time is not None:
            params["startTime"] = int(start_time)
        if end_time is not None:
            params["endTime"] = int(end_time)

        backoff = 1.0
        for _ in range(5):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{self.base_url}/api/v3/klines", params=params, headers=self._headers())
                    resp.raise_for_status()
                    data = resp.json()
                    return [self._normalize_kline(k) for k in data]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        return []

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        params = {"symbol": symbol.upper(), "limit": min(limit, 5000)}
        backoff = 1.0
        for _ in range(5):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{self.base_url}/api/v3/depth", params=params, headers=self._headers())
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        return {}

    async def stream_depth(self, symbol: str, levels: int = 20):
        stream = f"{symbol.lower()}@depth{levels}@100ms"
        url = f"wss://stream.binance.com:9443/ws/{stream}"
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1.0
                    async for msg in ws:
                        data = json.loads(msg)
                        bids = [[float(p), float(q)] for p, q in (data.get("bids") or [])[:levels]]
                        asks = [[float(p), float(q)] for p, q in (data.get("asks") or [])[:levels]]
                        yield {"bids": bids, "asks": asks, "event_time": data.get("E"), "last_update_id": data.get("u")}
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _normalize_kline(self, raw: List[Any]) -> Dict[str, Any]:
        return {
            "open_time": int(raw[0]),
            "open": float(raw[1]),
            "high": float(raw[2]),
            "low": float(raw[3]),
            "close": float(raw[4]),
            "volume": float(raw[5]),
            "close_time": int(raw[6]),
        }


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def ensure_symbols(session: AsyncSession, symbols: List[str]) -> None:
    """Insert missing symbols into the symbols table."""
    existing = set()
    res = await session.execute(Symbol.__table__.select())
    for row in res.mappings():
        existing.add(row["name"])
    for sym in symbols:
        if sym not in existing:
            session.add(Symbol(name=sym))
    await session.commit()


# ---------------------------------------------------------------------
# Ingestion routines
# ---------------------------------------------------------------------
async def upsert_candles(session: AsyncSession, client: BinanceClient, symbol: str, timeframe: str) -> int:
    klines = await client.get_klines(symbol, timeframe, limit=CANDLE_LOOKBACK)
    if not klines:
        return 0
    payload = []
    for k in klines:
        ts = datetime.fromtimestamp(k["open_time"] / 1000, tz=timezone.utc).replace(tzinfo=None)
        payload.append(
            {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "open": k["open"],
                "high": k["high"],
                "low": k["low"],
                "close": k["close"],
                "volume": k["volume"],
                "ts": ts,
            }
        )
    stmt = insert(Candle).values(payload)
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
    await session.execute(stmt)
    await session.commit()
    return len(payload)


def compute_imbalance(bids: list[list[float]], asks: list[list[float]]) -> float:
    bid_vol = sum(q for _, q in bids)
    ask_vol = sum(q for _, q in asks)
    denom = bid_vol + ask_vol
    return (bid_vol - ask_vol) / denom if denom > 0 else 0.0


async def write_orderbook_snapshot(session: AsyncSession, symbol: str, data: Dict[str, Any]) -> Optional[OrderbookSnapshot]:
    bids = [[float(p), float(q)] for p, q in (data.get("bids") or [])[:ORDERBOOK_LEVELS]]
    asks = [[float(p), float(q)] for p, q in (data.get("asks") or [])[:ORDERBOOK_LEVELS]]
    if not bids and not asks:
        return None
    spread = 0.0
    if bids and asks:
        spread = max(0.0, asks[0][0] - bids[0][0])
    ts_ms = data.get("event_time") or data.get("T")
    ts_val = _utc_now() if ts_ms is None else datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).replace(tzinfo=None)
    ob = OrderbookSnapshot(
        symbol=symbol.upper(),
        bids=bids,
        asks=asks,
        imbalance=compute_imbalance(bids, asks),
        spread=spread,
        ts=ts_val,
    )
    session.add(ob)
    await session.commit()
    await session.refresh(ob)
    return ob


# ---------------------------------------------------------------------
# Loops
# ---------------------------------------------------------------------
async def candle_loop(client: BinanceClient):
    while True:
        start = asyncio.get_event_loop().time()
        try:
            async with Session() as session:
                await ensure_symbols(session, SYMBOLS)
                for sym in SYMBOLS:
                    for tf in TIMEFRAMES:
                        written = await upsert_candles(session, client, sym, tf)
                        logger.info("candles %s %s upserted=%s", sym, tf, written)
        except Exception as exc:  # noqa: BLE001
            logger.exception("candle loop error: %s", exc)
        elapsed = asyncio.get_event_loop().time() - start
        await asyncio.sleep(max(CANDLE_INTERVAL_SEC - elapsed, 0.5))


async def orderbook_loop(client: BinanceClient):
    """Sample orderbook snapshots frequently; fall back to REST if WS unavailable."""
    while True:
        start = asyncio.get_event_loop().time()
        try:
            async with Session() as session:
                for sym in SYMBOLS:
                    data = await client.get_orderbook(sym, limit=ORDERBOOK_LEVELS)
                    if data:
                        await write_orderbook_snapshot(session, sym, data)
                        logger.info("orderbook %s snapshot stored", sym)
        except Exception as exc:  # noqa: BLE001
            logger.exception("orderbook loop error: %s", exc)
        elapsed = asyncio.get_event_loop().time() - start
        await asyncio.sleep(max(ORDERBOOK_INTERVAL_SEC - elapsed, 0.2))


async def main():
    client = BinanceClient()
    await asyncio.gather(candle_loop(client), orderbook_loop(client))


if __name__ == "__main__":
    asyncio.run(main())
