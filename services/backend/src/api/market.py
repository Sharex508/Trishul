from __future__ import annotations
from fastapi import APIRouter, Query
from typing import List, Optional

from src import crud, schemas

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/candles/latest", response_model=List[schemas.CandleOut])
async def latest_candles(
    symbol: str = Query(..., description="Trading symbol, e.g. BTCUSDT"),
    timeframe: str = Query(..., description="Binance interval: 1m,5m,15m,1h,1d"),
    limit: int = Query(200, ge=1, le=1000),
):
    return await crud.get_latest_candles(symbol, timeframe, limit=limit)


@router.get("/orderbook/latest", response_model=List[schemas.OrderbookSnapshotOut])
async def latest_orderbook(
    symbol: str = Query(..., description="Trading symbol, e.g. BTCUSDT"),
    limit: int = Query(50, ge=1, le=500),
):
    return await crud.get_latest_orderbooks(symbol, limit=limit)


@router.get("/features/latest", response_model=List[schemas.FeatureOut])
async def latest_features(
    symbol: str = Query(..., description="Trading symbol, e.g. BTCUSDT"),
    timeframe: str = Query(..., description="Feature timeframe (same as candle interval)"),
    limit: int = Query(50, ge=1, le=500),
):
    return await crud.get_latest_features(symbol, timeframe, limit=limit)
