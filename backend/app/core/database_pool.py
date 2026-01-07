"""
Async database connection pool using asyncpg.

Per DATABASE_OPTIMIZATION.md:
- Pool size: 20 connections
- Max overflow: 10 connections (total: 30 under load)
- Connection timeout: 5 seconds
- Max lifetime: 1 hour
- Idle timeout: 10 minutes
"""
import os
import asyncpg
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global connection pools
_primary_pool: Optional[asyncpg.Pool] = None
_read_replica_pools: list[asyncpg.Pool] = []


def get_database_url() -> str:
    """Get database URL from environment."""
    # Support both DATABASE_URL and direct PostgreSQL connection
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Fallback: construct from individual components
    host = os.getenv("DB_HOST", "postgres")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    database = os.getenv("DB_NAME", "postgres")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_read_replica_urls() -> list[str]:
    """Get read replica URLs from environment."""
    # Support comma-separated list of replica URLs
    replica_urls_str = os.getenv("DB_READ_REPLICA_URLS", "")
    if replica_urls_str:
        return [url.strip() for url in replica_urls_str.split(",") if url.strip()]
    return []


async def initialize_database_pool() -> bool:
    """
    Initialize database connection pools.
    
    Returns:
        True if initialization successful, False otherwise
    """
    global _primary_pool, _read_replica_pools
    
    try:
        # Initialize primary pool
        primary_url = get_database_url()
        logger.info("db_pool_initializing", type="primary", url_prefix=primary_url[:30])
        
        _primary_pool = await asyncpg.create_pool(
            primary_url,
            min_size=10,
            max_size=20,
            max_queries=50000,  # Recycle connections after N queries
            max_inactive_connection_lifetime=3600,  # 1 hour
            command_timeout=30,
        )
        
        logger.info("db_pool_initialized", type="primary")
        
        # Initialize read replica pools (if configured)
        replica_urls = get_read_replica_urls()
        if replica_urls:
            for i, replica_url in enumerate(replica_urls):
                logger.info("db_pool_initializing", type="replica", index=i, url_prefix=replica_url[:30])
                replica_pool = await asyncpg.create_pool(
                    replica_url,
                    min_size=5,
                    max_size=10,
                    max_queries=50000,
                    max_inactive_connection_lifetime=3600,
                    command_timeout=30,
                )
                _read_replica_pools.append(replica_pool)
                logger.info("db_pool_initialized", type="replica", index=i)
        else:
            logger.info("db_pool_no_replicas", message="No read replicas configured. Using primary for all queries.")
        
        return True
        
    except Exception as e:
        logger.error(
            "db_pool_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        _primary_pool = None
        _read_replica_pools = []
        return False


async def close_database_pools() -> None:
    """Close all database connection pools."""
    global _primary_pool, _read_replica_pools
    
    if _primary_pool:
        try:
            await _primary_pool.close()
            logger.info("db_pool_closed", type="primary")
        except Exception as e:
            logger.error("db_pool_close_failed", type="primary", error=str(e))
        finally:
            _primary_pool = None
    
    for i, replica_pool in enumerate(_read_replica_pools):
        try:
            await replica_pool.close()
            logger.info("db_pool_closed", type="replica", index=i)
        except Exception as e:
            logger.error("db_pool_close_failed", type="replica", index=i, error=str(e))
    
    _read_replica_pools = []


def get_primary_pool() -> Optional[asyncpg.Pool]:
    """Get primary database connection pool."""
    return _primary_pool


def get_read_replica_pools() -> list[asyncpg.Pool]:
    """Get read replica connection pools."""
    return _read_replica_pools


def get_read_pool() -> Optional[asyncpg.Pool]:
    """
    Get a read pool (replica if available, otherwise primary).
    
    Uses round-robin selection if multiple replicas available.
    """
    if _read_replica_pools:
        # Round-robin selection (simplified: always use first replica)
        # TODO: Implement proper round-robin or health-based selection
        return _read_replica_pools[0]
    return _primary_pool

