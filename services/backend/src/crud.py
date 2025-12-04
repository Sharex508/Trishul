from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import NoResultFound
from sqlalchemy.dialects.postgresql import insert
from . import db, models


async def get_symbols() -> List[models.Symbol]:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.Symbol).order_by(models.Symbol.name))
        return list(res.scalars().all())


# Admin credentials CRUD
async def get_api_credential(provider: str) -> models.ApiCredential | None:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.ApiCredential).where(models.ApiCredential.provider == provider))
        return res.scalar_one_or_none()


async def upsert_api_credential(provider: str, key_encrypted: str, secret_encrypted: str) -> models.ApiCredential:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.ApiCredential).where(models.ApiCredential.provider == provider))
        cred = res.scalar_one_or_none()
        now = __import__('datetime').datetime.utcnow()
        if cred is None:
            cred = models.ApiCredential(
                provider=provider,
                key_encrypted=key_encrypted,
                secret_encrypted=secret_encrypted,
                created_at=now,
                updated_at=now,
            )
            session.add(cred)
        else:
            cred.key_encrypted = key_encrypted
            cred.secret_encrypted = secret_encrypted
            cred.updated_at = now
        await session.commit()
        await session.refresh(cred)
        return cred


async def ensure_symbol(name: str) -> models.Symbol:
    name = name.upper()
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.Symbol).where(models.Symbol.name == name))
        symbol = res.scalar_one_or_none()
        if symbol is None:
            symbol = models.Symbol(name=name)
            session.add(symbol)
            await session.commit()
            await session.refresh(symbol)
        return symbol


async def insert_price(symbol_name: str, price: float) -> models.Price:
    symbol = await ensure_symbol(symbol_name)
    async with db.AsyncSession() as session:  # type: ignore
        p = models.Price(symbol_id=symbol.id, price=price)
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


async def get_latest_prices() -> List[models.Price]:
    async with db.AsyncSession() as session:  # type: ignore
        sub = (
            select(models.Price.symbol_id, func.max(models.Price.ts).label("max_ts"))
            .group_by(models.Price.symbol_id)
            .subquery()
        )
        stmt = (
            select(models.Price)
            .join(sub, (models.Price.symbol_id == sub.c.symbol_id) & (models.Price.ts == sub.c.max_ts))
            .order_by(models.Price.symbol_id)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())


async def get_recent_prices(symbol_name: str, limit: int = 50) -> List[models.Price]:
    """Return most recent price rows for a given symbol name, newest first."""
    async with db.AsyncSession() as session:  # type: ignore
        sym_res = await session.execute(select(models.Symbol).where(models.Symbol.name == symbol_name.upper()))
        symbol = sym_res.scalar_one_or_none()
        if symbol is None:
            return []
        res = await session.execute(
            select(models.Price)
            .where(models.Price.symbol_id == symbol.id)
            .order_by(models.Price.ts.desc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def add_ai_log(symbol_name: str, decision: str, confidence: float, rationale: str) -> models.AILog:
    symbol = await ensure_symbol(symbol_name)
    async with db.AsyncSession() as session:  # type: ignore
        log = models.AILog(symbol_id=symbol.id, decision=decision, confidence=confidence, rationale=rationale)
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log


async def get_ai_logs(limit: int = 100) -> List[models.AILog]:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.AILog).order_by(models.AILog.id.desc()).limit(limit))
        return list(res.scalars().all())


async def get_orders() -> List[models.Order]:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.Order).order_by(models.Order.id.desc()).limit(200))
        return list(res.scalars().all())


async def get_positions() -> List[models.Position]:
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(select(models.Position).order_by(models.Position.symbol_id))
        return list(res.scalars().all())


async def paper_execute_order(symbol_name: str, side: str, qty: float, price: float) -> models.Order:
    symbol = await ensure_symbol(symbol_name)
    async with db.AsyncSession() as session:  # type: ignore
        order = models.Order(symbol_id=symbol.id, side=side, qty=qty, price=price, status="FILLED")
        session.add(order)
        # upsert position
        res = await session.execute(select(models.Position).where(models.Position.symbol_id == symbol.id))
        pos = res.scalar_one_or_none()
        if pos is None:
            pos = models.Position(symbol_id=symbol.id, qty=0.0, avg_price=0.0)
            session.add(pos)
            await session.flush()
        # simple average price logic
        if side.upper() == "BUY":
            new_qty = pos.qty + qty
            pos.avg_price = (pos.avg_price * pos.qty + price * qty) / new_qty if new_qty != 0 else 0.0
            pos.qty = new_qty
        elif side.upper() == "SELL":
            pos.qty = max(0.0, pos.qty - qty)
            if pos.qty == 0:
                pos.avg_price = 0.0
        await session.commit()
        await session.refresh(order)
        return order


async def reset_session() -> None:
    """Clear orders, positions, prices, and AI logs to start fresh session."""
    async with db.AsyncSession() as session:  # type: ignore
        await session.execute(delete(models.Order))
        await session.execute(delete(models.Position))
        await session.execute(delete(models.Price))
        await session.execute(delete(models.AILog))
        await session.commit()


async def reset_prices() -> None:
    """Delete all rows from prices table (symbols remain)."""
    async with db.AsyncSession() as session:  # type: ignore
        await session.execute(delete(models.Price))
        await session.commit()


# ---------------- Market data ingestion helpers ----------------
async def upsert_candles(rows: List[models.Candle]) -> int:
    """Bulk upsert candle rows by (symbol, timeframe, ts). Returns affected row count."""
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
    async with db.AsyncSession() as session:  # type: ignore
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
        rowcount = res.rowcount or len(payload)
        return rowcount


async def insert_orderbook_snapshot(
    symbol: str, bids: list, asks: list, imbalance: float, spread: float, ts: datetime
) -> models.OrderbookSnapshot:
    symbol = symbol.upper()
    async with db.AsyncSession() as session:  # type: ignore
        ob = models.OrderbookSnapshot(
            symbol=symbol,
            bids=bids,
            asks=asks,
            imbalance=imbalance,
            spread=spread,
            ts=ts,
        )
        session.add(ob)
        await session.commit()
        await session.refresh(ob)
        return ob


async def insert_features(symbol: str, timeframe: str, feature_json: dict, ts: datetime) -> models.Feature:
    symbol = symbol.upper()
    async with db.AsyncSession() as session:  # type: ignore
        stmt = insert(models.Feature).values(
            symbol=symbol, timeframe=timeframe, feature_json=feature_json, ts=ts
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "ts"], set_={"feature_json": stmt.excluded.feature_json}  # type: ignore[attr-defined]
        )
        await session.execute(stmt)
        await session.commit()
        res = await session.execute(
            select(models.Feature)
            .where(models.Feature.symbol == symbol, models.Feature.timeframe == timeframe, models.Feature.ts == ts)
            .limit(1)
        )
        return res.scalar_one()


async def get_latest_candles(symbol: str, timeframe: str, limit: int = 200) -> List[models.Candle]:
    symbol = symbol.upper()
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(
            select(models.Candle)
            .where(models.Candle.symbol == symbol, models.Candle.timeframe == timeframe)
            .order_by(models.Candle.ts.desc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def get_latest_orderbooks(symbol: str, limit: int = 50) -> List[models.OrderbookSnapshot]:
    symbol = symbol.upper()
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(
            select(models.OrderbookSnapshot)
            .where(models.OrderbookSnapshot.symbol == symbol)
            .order_by(models.OrderbookSnapshot.ts.desc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def get_latest_features(symbol: str, timeframe: str, limit: int = 50) -> List[models.Feature]:
    symbol = symbol.upper()
    async with db.AsyncSession() as session:  # type: ignore
        res = await session.execute(
            select(models.Feature)
            .where(models.Feature.symbol == symbol, models.Feature.timeframe == timeframe)
            .order_by(models.Feature.ts.desc())
            .limit(limit)
        )
        return list(res.scalars().all())
