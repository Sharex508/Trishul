from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .config import settings


Base = declarative_base()
engine = None
AsyncSession: async_sessionmaker[_AsyncSession] | None = None


def _dsn() -> str:
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


async def init_engine_and_session():
    global engine, AsyncSession
    if engine is None:
        engine = create_async_engine(_dsn(), echo=False, future=True)
        AsyncSession = async_sessionmaker(bind=engine, class_=_AsyncSession, expire_on_commit=False)


async def create_all():
    from . import models  # ensure models are imported
    async with engine.begin() as conn:  # type: ignore
        await conn.run_sync(models.Base.metadata.create_all)
