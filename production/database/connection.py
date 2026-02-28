"""Database connection pool management using asyncpg.

Provides async PostgreSQL connection pool with health checks
for the Customer Success Digital FTE CRM.
"""

import os
import logging
from contextlib import asynccontextmanager

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """Initialize the asyncpg connection pool (min=5, max=20)."""
    global _pool
    if _pool is not None:
        return _pool

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://fte_user:fte_pass@localhost:5432/fte_crm",
    )
    # Neon requires SSL; strip channel_binding param (asyncpg handles it natively)
    database_url = database_url.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?").replace("?channel_binding=require", "")
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
        ssl="require" if "neon.tech" in database_url else None,
    )
    logger.info("Database connection pool initialized (min=5, max=20)")
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Return the current pool, initializing if needed."""
    if _pool is None:
        return await init_pool()
    return _pool


async def close_pool() -> None:
    """Gracefully close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_connection():
    """Acquire a connection from the pool as an async context manager."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def health_check() -> dict:
    """Run a health check query against the database.

    Returns:
        dict with 'status' ('healthy'/'unhealthy') and optional 'error'.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "unexpected query result"}
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}
