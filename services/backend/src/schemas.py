from datetime import datetime
from typing import Any, List
from pydantic import BaseModel


class SymbolOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PriceOut(BaseModel):
    id: int
    symbol_id: int
    price: float
    ts: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    symbol_id: int
    side: str
    qty: float
    price: float
    status: str
    ts: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    qty: float
    price: float | None = None


class PositionOut(BaseModel):
    id: int
    symbol_id: int
    qty: float
    avg_price: float
    updated_at: datetime

    class Config:
        from_attributes = True


class AILogOut(BaseModel):
    id: int
    symbol_id: int
    decision: str
    confidence: float
    rationale: str
    ts: datetime

    class Config:
        from_attributes = True


class IntentionOut(BaseModel):
    symbol: str
    action: str  # BUY/SELL/HOLD
    size: float
    confidence: float
    explanation: str


class CandleOut(BaseModel):
    id: int
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ts: datetime

    class Config:
        from_attributes = True


class OrderbookSnapshotOut(BaseModel):
    id: int
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    imbalance: float
    spread: float
    ts: datetime

    class Config:
        from_attributes = True


class FeatureOut(BaseModel):
    id: int
    symbol: str
    timeframe: str
    feature_json: Any
    ts: datetime

    class Config:
        from_attributes = True
