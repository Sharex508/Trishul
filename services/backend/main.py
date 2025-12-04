from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
from typing import List, Dict, Optional

from src.config import settings
from src.db import init_engine_and_session
from src import crud, models, schemas
from src.crypto_utils import encrypt_pair, mask_key
from src.api.monitor import router as monitor_router
from src.api.trading import router as trading_router
from src.api.ai import router as ai_router
from src.api.market import router as market_router


price_subscribers: List[WebSocket] = []

class CredentialIn(BaseModel):
    provider: str = "binance"
    api_key: str
    api_secret: str

class CredentialMaskedOut(BaseModel):
    provider: str
    api_key_masked: str
    updated_at: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB engine/session will be initialized on startup; Alembic runs in entrypoint
    await init_engine_and_session()
    # seed symbols
    existing = await crud.get_symbols()
    if not existing:
        for s in settings.PRICE_SYMBOLS_LIST:
            await crud.ensure_symbol(s)
    yield


app = FastAPI(title="Crypto AI Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers under /v1 (non-breaking; legacy routes remain)
app.include_router(monitor_router, prefix="/v1")
app.include_router(trading_router, prefix="/v1")
app.include_router(ai_router, prefix="/v1")
app.include_router(market_router, prefix="/v1")


def _require_admin(token: Optional[str]):
    if not token or token != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"name": "Crypto AI Platform", "version": app.version}


@app.get("/metrics")
async def metrics():
    # minimal placeholder; integrate Prometheus later
    return {"uptime": "n/a", "symbols": settings.PRICE_SYMBOLS_LIST}


@app.get("/config")
async def get_config():
    return {
        "timezone": settings.TIMEZONE,
        "symbols": settings.PRICE_SYMBOLS,
        "paper_trading": True,
    }


@app.get("/symbols", response_model=List[schemas.SymbolOut])
async def symbols():
    return await crud.get_symbols()


@app.get("/prices/latest", response_model=List[schemas.PriceOut])
async def prices_latest():
    return await crud.get_latest_prices()


@app.get("/orders", response_model=List[schemas.OrderOut])
async def orders():
    return await crud.get_orders()


@app.get("/positions", response_model=List[schemas.PositionOut])
async def positions():
    return await crud.get_positions()


@app.get("/ai/logs", response_model=List[schemas.AILogOut])
async def ai_logs():
    return await crud.get_ai_logs(limit=100)


# Admin credentials endpoints
@app.post("/admin/credentials", response_model=CredentialMaskedOut)
async def save_credentials(payload: CredentialIn, x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    _require_admin(x_admin_token)
    key_enc, secret_enc = encrypt_pair(payload.api_key, payload.api_secret)
    cred = await crud.upsert_api_credential(provider=payload.provider, key_encrypted=key_enc, secret_encrypted=secret_enc)
    return CredentialMaskedOut(provider=cred.provider, api_key_masked=mask_key(payload.api_key), updated_at=cred.updated_at.isoformat())


@app.get("/admin/credentials", response_model=CredentialMaskedOut)
async def get_credentials(provider: str = "binance", x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    _require_admin(x_admin_token)
    cred = await crud.get_api_credential(provider)
    if not cred:
        return CredentialMaskedOut(provider=provider, api_key_masked="", updated_at=None)
    # We do not decrypt on GET; only return masked info
    return CredentialMaskedOut(provider=cred.provider, api_key_masked="***", updated_at=cred.updated_at.isoformat())


@app.websocket("/ws/prices")
async def ws_prices(ws: WebSocket):
    await ws.accept()
    price_subscribers.append(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive pings from client
    except WebSocketDisconnect:
        pass
    finally:
        if ws in price_subscribers:
            price_subscribers.remove(ws)


async def broadcast_price_update(message: Dict):
    coros = []
    for ws in list(price_subscribers):
        try:
            coros.append(ws.send_json(message))
        except Exception:
            pass
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)


# internal hook used by worker (optional future import)
async def on_new_price(price: schemas.PriceOut):
    await broadcast_price_update({"type": "price", "data": price.model_dump()})
