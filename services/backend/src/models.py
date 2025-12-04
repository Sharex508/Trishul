from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base


class Symbol(Base):
    __tablename__ = "symbols"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prices: Mapped[list["Price"]] = relationship("Price", back_populates="symbol")

class Price(Base):
    __tablename__ = "prices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), index=True)
    price: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)

    symbol: Mapped[Symbol] = relationship("Symbol", back_populates="prices")
    __table_args__ = (UniqueConstraint("symbol_id", "ts", name="uq_price_symbol_ts"),)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    side: Mapped[str] = mapped_column(String(4))  # BUY/SELL
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="FILLED")
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    symbol: Mapped[Symbol] = relationship("Symbol")


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), unique=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    symbol: Mapped[Symbol] = relationship("Symbol")


class AILog(Base):
    __tablename__ = "ai_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    decision: Mapped[str] = mapped_column(String(32))  # BUY/SELL/HOLD
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(String(1024), default="")
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    symbol: Mapped[Symbol] = relationship("Symbol")


class ApiCredential(Base):
    __tablename__ = "api_credentials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g., 'binance'
    key_encrypted: Mapped[str] = mapped_column(String(512))
    secret_encrypted: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
