from __future__ import annotations
from typing import List
from fastapi import APIRouter
from src import crud, schemas
from src.marketdata import reset_trending_state

router = APIRouter(prefix="/trading", tags=["trading"]) 

# In-memory trading enable flag (starts disabled; enable via POST /start)
TRADING_ENABLED: bool = False


@router.get("/status")
async def trading_status():
    return {"enabled": TRADING_ENABLED}


@router.post("/start")
async def trading_start():
    global TRADING_ENABLED
    TRADING_ENABLED = True
    return {"enabled": TRADING_ENABLED}


@router.post("/stop")
async def trading_stop():
    global TRADING_ENABLED
    TRADING_ENABLED = False
    return {"enabled": TRADING_ENABLED}


@router.post("/reset")
async def trading_reset_prices_only():
    """Clear prices only and reset session-based trending state; symbols remain."""
    await crud.reset_prices()
    reset_trending_state()
    return {"ok": True}


@router.get("/orders", response_model=List[schemas.OrderOut])
async def orders_v1():
    return await crud.get_orders()


@router.get("/positions", response_model=List[schemas.PositionOut])
async def positions_v1():
    return await crud.get_positions()
