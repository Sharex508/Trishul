from __future__ import annotations
import asyncio
import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import websockets


class BinanceClient:
    """Lightweight Binance REST and WebSocket client with basic backoff handling."""

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
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical klines and return normalized dicts."""
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
                # Handle Binance rate limits gracefully
                if exc.response.status_code == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        return []

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Fetch a depth snapshot over REST (useful as a fallback)."""
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

    async def stream_depth(self, symbol: str, levels: int = 20) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield depth updates over WebSocket; automatically reconnect on disconnect."""
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
                        yield {
                            "bids": bids,
                            "asks": asks,
                            "event_time": data.get("E"),
                            "last_update_id": data.get("u") or data.get("lastUpdateId"),
                        }
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _normalize_kline(self, raw: List[Any]) -> Dict[str, Any]:
        """Map Binance kline array -> dict with typed fields."""
        return {
            "open_time": int(raw[0]),
            "open": float(raw[1]),
            "high": float(raw[2]),
            "low": float(raw[3]),
            "close": float(raw[4]),
            "volume": float(raw[5]),
            "close_time": int(raw[6]),
        }
