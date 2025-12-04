from __future__ import annotations
from fastapi import APIRouter
from typing import List
from src import crud, schemas
from src.marketdata import get_top24, get_trending

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/symbols", response_model=List[schemas.SymbolOut])
async def symbols_v1():
    return await crud.get_symbols()


@router.get("/prices/latest", response_model=List[schemas.PriceOut])
async def prices_latest_v1():
    return await crud.get_latest_prices()


@router.get("/top24h")
async def top24h():
    """Return top gainers/losers for Spot USDT pairs from cached Binance 24h stats.
    Response shape: {updated_at: float(epoch), stale: bool, gainers: [...], losers: [...], universe_size: int, filters: {...}}
    """
    return await get_top24()


@router.get("/trending")
async def trending():
    """Return session-based gainers/losers using live DB prices (Coin Monitor style)."""
    return await get_trending()
