from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class OrderResult:
    order_id: str
    status: str
    price: float
    qty: float
    side: str  # BUY/SELL


class ExchangeAdapter(ABC):
    @abstractmethod
    async def ensure_symbol(self, symbol: str) -> None: ...

    @abstractmethod
    async def get_price(self, symbol: str) -> float: ...

    @abstractmethod
    async def create_order(self, symbol: str, side: str, qty: float, price: Optional[float] = None) -> OrderResult: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None: ...

    @abstractmethod
    async def get_balance(self, asset: str) -> float: ...


class DryRunAdapter(ExchangeAdapter):
    """In-memory simulator. Does not hit any external API."""
    def __init__(self):
        self._balances: dict[str, float] = {"USDT": 100000.0}
        self._last_id = 0
        self._prices: dict[str, float] = {}

    async def ensure_symbol(self, symbol: str) -> None:
        self._prices.setdefault(symbol, 1.0)

    async def get_price(self, symbol: str) -> float:
        return self._prices.get(symbol, 1.0)

    async def create_order(self, symbol: str, side: str, qty: float, price: Optional[float] = None) -> OrderResult:
        self._last_id += 1
        p = price if price is not None else await self.get_price(symbol)
        return OrderResult(order_id=str(self._last_id), status="FILLED", price=p, qty=qty, side=side.upper())

    async def cancel_order(self, order_id: str) -> None:
        return None

    async def get_balance(self, asset: str) -> float:
        return self._balances.get(asset, 0.0)


class BinanceAdapter(ExchangeAdapter):
    """Skeleton adapter; full implementation wired later."""
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, use_testnet: bool = False):
        # Defer heavy imports to keep backend startup light
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.use_testnet = use_testnet or (os.getenv("BINANCE_USE_TESTNET", "false").lower() == "true")
        # Actual client initialization will be added later

    async def ensure_symbol(self, symbol: str) -> None:  # pragma: no cover - stub
        return None

    async def get_price(self, symbol: str) -> float:  # pragma: no cover - stub
        raise NotImplementedError("BinanceAdapter.get_price not implemented yet")

    async def create_order(self, symbol: str, side: str, qty: float, price: Optional[float] = None) -> OrderResult:  # pragma: no cover - stub
        raise NotImplementedError("BinanceAdapter.create_order not implemented yet")

    async def cancel_order(self, order_id: str) -> None:  # pragma: no cover - stub
        raise NotImplementedError("BinanceAdapter.cancel_order not implemented yet")

    async def get_balance(self, asset: str) -> float:  # pragma: no cover - stub
        raise NotImplementedError("BinanceAdapter.get_balance not implemented yet")
