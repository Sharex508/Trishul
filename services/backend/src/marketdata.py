import asyncio
import time
from typing import Dict, List, Tuple

import httpx

from .config import settings
from . import crud

# Caches
_universe_cache: Dict[str, object] = {
    "symbols": [],
    "updated_at": 0.0,
}

_top24_cache: Dict[str, object] = {
    "updated_at": 0.0,
    "stale": True,
    "gainers": [],
    "losers": [],
    "universe_size": 0,
    "filters": {},
}

# Session-based trending cache (Coin Monitor style)
_trending_cache: Dict[str, object] = {
    "updated_at": 0.0,
    "stale": True,
    "gainers": [],
    "losers": [],
    "universe_size": 0,
    "meta": {},
}

# Per-symbol trending state kept in-memory
_trending_state: Dict[str, Dict[str, float]] = {}  # symbol -> {first, high, low, last_local_low}


EXCLUDE_SUFFIXES = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def reset_trending_state():
    """Clear in-memory session-based trending caches/state."""
    _trending_state.clear()
    _trending_cache.update({
        "updated_at": 0.0,
        "stale": True,
        "gainers": [],
        "losers": [],
        "universe_size": 0,
        "meta": {},
        "filters": {"label": "Session-based"},
    })


async def _fetch_exchange_info() -> List[str]:
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            out = []
            for s in data.get("symbols", []):
                if s.get("status") != "TRADING":
                    continue
                if s.get("quoteAsset") != "USDT":
                    continue
                perms = s.get("permissions")
                # Some Binance gateways omit 'permissions'; treat isSpotTradingAllowed==True as sufficient for spot
                if perms is not None and "SPOT" not in perms:
                    continue
                if not s.get("isSpotTradingAllowed", True):
                    continue
                symbol = s.get("symbol")
                if symbol and not any(symbol.endswith(sfx) for sfx in EXCLUDE_SUFFIXES):
                    out.append(symbol)
            return out
    except Exception:
        return []


async def get_usdt_universe() -> List[str]:
    now = time.time()
    ttl = int(getattr(settings, "USDT_UNIVERSE_REFRESH_SEC", 1800))
    # Refresh cache if expired or empty
    if now - float(_universe_cache.get("updated_at", 0.0)) > ttl or not _universe_cache.get("symbols"):
        syms = await _fetch_exchange_info()
        if syms:
            _universe_cache["symbols"] = syms
            _universe_cache["updated_at"] = now
        elif _universe_cache.get("symbols"):
            # keep previous cached symbols if fetch failed
            pass
        else:
            # First-run fallback to configured symbols from settings
            fallback = [s.strip().upper() for s in settings.PRICE_SYMBOLS.split(",") if s.strip()]
            _universe_cache["symbols"] = fallback
            _universe_cache["updated_at"] = now
    return list(_universe_cache.get("symbols", []))


async def _fetch_24h_stats_batch(symbols: List[str]) -> List[dict]:
    if not symbols:
        return []
    url = "https://api.binance.com/api/v3/ticker/24hr"
    # Batch using symbols param (max ~100 per request)
    out: List[dict] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(0, len(symbols), 100):
                chunk = symbols[i : i + 100]
                params = {"symbols": httpx.QueryParams.encode_value(chunk)}  # not ideal; build manually below
                # Build query manually to ensure proper encoding of list
                q = "[" + ",".join(f'"{s}"' for s in chunk) + "]"
                resp = await client.get(url, params={"symbols": q})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict):
                    # Some gateways may return a dict; skip
                    continue
                out.extend(data)
        return out
    except Exception:
        return []


def _parse_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


async def refresh_top24_cache() -> Dict[str, object]:
    universe = await get_usdt_universe()
    stats = await _fetch_24h_stats_batch(universe)
    price_floor = float(getattr(settings, "TOP24H_PRICE_FLOOR", 0.0001))

    rows: List[dict] = []
    for d in stats:
        sym = d.get("symbol")
        if not sym:
            continue
        last = _parse_float(d.get("lastPrice"))
        pct = _parse_float(d.get("priceChangePercent"))
        if last < price_floor:
            continue
        rows.append(
            {
                "symbol": sym,
                "lastPrice": last,
                "highPrice": _parse_float(d.get("highPrice")),
                "lowPrice": _parse_float(d.get("lowPrice")),
                "priceChangePercent": pct,
                "quoteVolume": _parse_float(d.get("quoteVolume")),
            }
        )

    # Top-N by 24h quote volume
    topn = int(getattr(settings, "TOP24H_TOPN", 200))
    rows.sort(key=lambda r: r["quoteVolume"], reverse=True)
    liquid = rows[:topn]

    # Gainers/Losers among liquid set
    gainers = sorted(liquid, key=lambda r: r["priceChangePercent"], reverse=True)[:10]
    losers = sorted(liquid, key=lambda r: r["priceChangePercent"])[:10]

    now = time.time()
    _top24_cache.update(
        {
            "updated_at": now,
            "stale": False,
            "gainers": gainers,
            "losers": losers,
            "universe_size": len(universe),
            "filters": {
                "topn": topn,
                "price_floor": price_floor,
                "universe_cached_at": _universe_cache.get("updated_at", 0.0),
            },
        }
    )
    return _top24_cache


async def get_top24() -> Dict[str, object]:
    ttl = int(getattr(settings, "TOP24H_REFRESH_SEC", 20))
    now = time.time()
    # If cache expired, try refresh (non-blocking safety)
    if now - float(_top24_cache.get("updated_at", 0.0)) > ttl:
        try:
            return await refresh_top24_cache()
        except Exception:
            # mark stale and return previous
            _top24_cache["stale"] = True
    return _top24_cache.copy()

# ---------------- Session-based trending (Coin Monitor style) ----------------
async def _latest_prices_map_by_symbol() -> Dict[str, float]:
    """Load latest prices from DB and return {symbol_name: price}."""
    prices = await crud.get_latest_prices()
    symbols = await crud.get_symbols()
    id_to_name = {s.id: s.name for s in symbols}
    out: Dict[str, float] = {}
    for p in prices:
        name = id_to_name.get(p.symbol_id)
        if not name:
            continue
        out[name] = float(p.price)
    return out


async def refresh_trending_cache() -> Dict[str, object]:
    loss_pct = float(getattr(settings, "MONITOR_LOSS_THRESHOLD_PCT", 2.0))
    recovery_pct = float(getattr(settings, "MONITOR_RECOVERY_PCT", 0.5))

    price_map = await _latest_prices_map_by_symbol()
    universe = sorted(price_map.keys())

    gainers: List[dict] = []
    losers: List[dict] = []

    for sym, price in price_map.items():
        st = _trending_state.get(sym)
        if st is None:
            st = {
                "first": price,
                "high": price,
                "low": price,
                "last_local_low": price,
            }
            _trending_state[sym] = st
        # update highs/lows
        if price > st["high"]:
            st["high"] = price
        if price < st["low"]:
            st["low"] = price
            st["last_local_low"] = price

        # Loser: price fell >= loss_pct from session high
        if st["high"] > 0 and price <= st["high"] * (1 - loss_pct / 100.0):
            drop_pct = (st["high"] - price) / st["high"] * 100.0
            losers.append({
                "symbol": sym,
                "lastPrice": price,
                "highPrice": st["high"],
                "lowPrice": st["low"],
                "priceChangePercent": -round(drop_pct, 4),
            })

        # Gainer: either new session high, or recovered >= recovery_pct from recent local low
        gained = False
        gain_pct = 0.0
        if price >= st["high"]:  # new high
            base = max(st["first"], 1e-12)
            gain_pct = (price / base - 1.0) * 100.0
            gained = True
        elif price >= st["last_local_low"] * (1 + recovery_pct / 100.0):
            base = max(st["last_local_low"], 1e-12)
            gain_pct = (price / base - 1.0) * 100.0
            gained = True
        if gained and gain_pct > 0:
            gainers.append({
                "symbol": sym,
                "lastPrice": price,
                "highPrice": st["high"],
                "lowPrice": st["low"],
                "priceChangePercent": round(gain_pct, 4),
            })

    # sort and cut to top 10 by magnitude
    gainers.sort(key=lambda r: r["priceChangePercent"], reverse=True)
    losers.sort(key=lambda r: r["priceChangePercent"])  # negative values first
    gainers = gainers[:10]
    losers = losers[:10]

    now = time.time()
    _trending_cache.update({
        "updated_at": now,
        "stale": False,
        "gainers": gainers,
        "losers": losers,
        "universe_size": len(universe),
        "meta": {
            "loss_pct": loss_pct,
            "recovery_pct": recovery_pct,
            "label": "Session-based",
        },
        "filters": {"label": "Session-based"},
    })
    return _trending_cache


async def get_trending() -> Dict[str, object]:
    ttl = int(getattr(settings, "TRENDING_REFRESH_SEC", 10))
    now = time.time()
    if now - float(_trending_cache.get("updated_at", 0.0)) > ttl:
        try:
            return await refresh_trending_cache()
        except Exception:
            _trending_cache["stale"] = True
    return _trending_cache.copy()
