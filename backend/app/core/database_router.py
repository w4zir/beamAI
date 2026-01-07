"""
Database read/write routing logic.

Per DATABASE_OPTIMIZATION.md:
- Route read queries (search, recommendations) to replicas
- Route write queries (events) to primary
- Monitor replication lag (alert if >60s)
"""
import asyncio
import time
from typing import Optional, List, Dict, Any
import asyncpg
from app.core.database_pool import get_primary_pool, get_read_pool
from app.core.logging import get_logger
from app.core.metrics import (
    record_db_query_duration,
    update_replication_lag,
    update_replica_health,
)

logger = get_logger(__name__)


async def execute_read_query(
    query: str,
    *args,
    query_type: str = "read",
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Execute a read query (routes to replica if available).
    
    Args:
        query: SQL query string
        *args: Query parameters
        query_type: Type of query for metrics ("search", "recommendation", "feature")
        timeout: Query timeout in seconds
    
    Returns:
        List of result dictionaries
    """
    start_time = time.time()
    pool = get_read_pool()
    
    if not pool:
        logger.error("db_read_pool_unavailable", query_type=query_type)
        raise RuntimeError("Database read pool not available")
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            
            # Convert asyncpg.Record to dict
            results = [dict(row) for row in rows]
            
            duration = time.time() - start_time
            record_db_query_duration(query_type, duration)
            
            return results
            
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        record_db_query_duration(query_type, duration)
        logger.error("db_query_timeout", query_type=query_type, timeout=timeout)
        raise
    except Exception as e:
        duration = time.time() - start_time
        record_db_query_duration(query_type, duration)
        logger.error(
            "db_read_query_error",
            query_type=query_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


async def execute_write_query(
    query: str,
    *args,
    query_type: str = "write",
    timeout: float = 30.0,
) -> Optional[Any]:
    """
    Execute a write query (always routes to primary).
    
    Args:
        query: SQL query string
        *args: Query parameters
        query_type: Type of query for metrics ("event", "product_update", etc.)
        timeout: Query timeout in seconds
    
    Returns:
        Query result (if any)
    """
    start_time = time.time()
    pool = get_primary_pool()
    
    if not pool:
        logger.error("db_write_pool_unavailable", query_type=query_type)
        raise RuntimeError("Database write pool not available")
    
    try:
        async with pool.acquire() as conn:
            result = await conn.execute(query, *args)
            
            duration = time.time() - start_time
            record_db_query_duration(query_type, duration)
            
            return result
            
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        record_db_query_duration(query_type, duration)
        logger.error("db_query_timeout", query_type=query_type, timeout=timeout)
        raise
    except Exception as e:
        duration = time.time() - start_time
        record_db_query_duration(query_type, duration)
        logger.error(
            "db_write_query_error",
            query_type=query_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


async def check_replication_lag() -> Dict[str, float]:
    """
    Check replication lag for all replicas.
    
    Returns:
        Dictionary mapping replica index to lag in seconds
    """
    from app.core.database_pool import get_read_replica_pools
    
    replica_pools = get_read_replica_pools()
    lag_results = {}
    
    for i, pool in enumerate(replica_pools):
        try:
            async with pool.acquire() as conn:
                # Query replication lag (PostgreSQL specific)
                # This query works for streaming replication
                lag_row = await conn.fetchrow(
                    """
                    SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
                    """
                )
                
                if lag_row:
                    lag_seconds = lag_row["lag_seconds"] or 0.0
                    lag_results[f"replica_{i}"] = lag_seconds
                    update_replication_lag(f"replica_{i}", lag_seconds)
                    
                    # Check health (healthy if lag < 60 seconds)
                    healthy = lag_seconds < 60.0
                    update_replica_health(f"replica_{i}", healthy)
                    
                    if lag_seconds > 60.0:
                        logger.warning(
                            "db_replication_lag_high",
                            replica=f"replica_{i}",
                            lag_seconds=lag_seconds,
                        )
        except Exception as e:
            logger.warning(
                "db_replication_lag_check_failed",
                replica=f"replica_{i}",
                error=str(e),
            )
            update_replica_health(f"replica_{i}", False)
            lag_results[f"replica_{i}"] = -1.0  # Unknown lag
    
    return lag_results

