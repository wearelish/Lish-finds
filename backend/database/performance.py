"""
Database performance optimization utilities.

Includes query analysis, index recommendations, and performance monitoring.
"""

import time
from typing import Dict, List, Any, Optional
import asyncio
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session, get_engine
from core.config import settings

logger = structlog.get_logger(__name__)

# Query performance tracking
query_stats: Dict[str, Dict] = {}


class QueryProfiler:
    """Context manager for profiling database queries."""
    
    def __init__(self, query_name: str, session: AsyncSession):
        self.query_name = query_name
        self.session = session
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.time()
        logger.debug("Starting query", query=self.query_name)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # Track query statistics
        if self.query_name not in query_stats:
            query_stats[self.query_name] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "max_time": 0,
                "min_time": float('inf'),
                "errors": 0
            }
        
        stats = query_stats[self.query_name]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["max_time"] = max(stats["max_time"], duration)
        stats["min_time"] = min(stats["min_time"], duration)
        
        if exc_type:
            stats["errors"] += 1
            logger.error(
                "Query failed",
                query=self.query_name,
                duration=duration,
                error=str(exc_val)
            )
        else:
            logger.debug(
                "Query completed", 
                query=self.query_name,
                duration=duration
            )
            
            # Log slow queries
            if duration > 1.0:  # Queries taking more than 1 second
                logger.warning(
                    "Slow query detected",
                    query=self.query_name,
                    duration=duration
                )


async def analyze_table_performance(table_name: str) -> Dict[str, Any]:
    """Analyze performance metrics for a specific table."""
    if "sqlite" in settings.DATABASE_URL:
        return await _analyze_sqlite_table(table_name)
    else:
        return await _analyze_postgres_table(table_name)


async def _analyze_postgres_table(table_name: str) -> Dict[str, Any]:
    """Analyze PostgreSQL table performance."""
    async with get_db_session() as session:
        
        # Table size and statistics
        size_query = text("""
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation,
                most_common_vals,
                most_common_freqs
            FROM pg_stats 
            WHERE tablename = :table_name
        """)
        
        table_size_query = text("""
            SELECT 
                pg_size_pretty(pg_total_relation_size(:table_name)) as total_size,
                pg_size_pretty(pg_relation_size(:table_name)) as table_size,
                pg_size_pretty(pg_total_relation_size(:table_name) - pg_relation_size(:table_name)) as index_size
        """)
        
        # Index usage statistics
        index_query = text("""
            SELECT 
                indexrelname as index_name,
                idx_tup_read,
                idx_tup_fetch,
                idx_scan,
                idx_tup_read / NULLIF(idx_scan, 0) as avg_tuples_per_scan
            FROM pg_stat_user_indexes 
            WHERE relname = :table_name
        """)
        
        try:
            # Execute queries
            stats_result = await session.execute(size_query, {"table_name": table_name})
            size_result = await session.execute(table_size_query, {"table_name": table_name})
            index_result = await session.execute(index_query, {"table_name": table_name})
            
            return {
                "table_name": table_name,
                "column_stats": [dict(row) for row in stats_result.fetchall()],
                "size_info": dict(size_result.fetchone()) if size_result else {},
                "index_stats": [dict(row) for row in index_result.fetchall()],
            }
            
        except Exception as e:
            logger.error("Failed to analyze PostgreSQL table", table=table_name, error=str(e))
            return {"error": str(e)}


async def _analyze_sqlite_table(table_name: str) -> Dict[str, Any]:
    """Analyze SQLite table performance."""
    async with get_db_session() as session:
        try:
            # Table info
            pragma_query = text(f"PRAGMA table_info({table_name})")
            index_query = text(f"PRAGMA index_list({table_name})")
            
            table_info = await session.execute(pragma_query)
            index_info = await session.execute(index_query)
            
            return {
                "table_name": table_name,
                "columns": [dict(row) for row in table_info.fetchall()],
                "indexes": [dict(row) for row in index_info.fetchall()],
            }
            
        except Exception as e:
            logger.error("Failed to analyze SQLite table", table=table_name, error=str(e))
            return {"error": str(e)}


async def get_slow_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """Get the slowest queries from statistics."""
    slow_queries = []
    
    for query_name, stats in query_stats.items():
        if stats["count"] > 0:
            slow_queries.append({
                "query": query_name,
                "avg_time": stats["avg_time"],
                "max_time": stats["max_time"],
                "count": stats["count"],
                "total_time": stats["total_time"],
                "error_rate": stats["errors"] / stats["count"]
            })
    
    # Sort by average time descending
    slow_queries.sort(key=lambda x: x["avg_time"], reverse=True)
    return slow_queries[:limit]


async def suggest_indexes() -> List[Dict[str, Any]]:
    """Suggest database indexes based on query patterns."""
    if "sqlite" in settings.DATABASE_URL:
        return []  # SQLite auto-indexing is usually sufficient
    
    async with get_db_session() as session:
        try:
            # Find tables with sequential scans
            seq_scan_query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    n_tup_ins + n_tup_upd + n_tup_del as modifications
                FROM pg_stat_user_tables
                WHERE seq_scan > idx_scan
                AND seq_tup_read > 1000
                ORDER BY seq_tup_read DESC
            """)
            
            result = await session.execute(seq_scan_query)
            suggestions = []
            
            for row in result.fetchall():
                suggestions.append({
                    "table": f"{row.schemaname}.{row.tablename}",
                    "reason": "High sequential scan ratio",
                    "seq_scans": row.seq_scan,
                    "seq_tuples_read": row.seq_tup_read,
                    "index_scans": row.idx_scan,
                    "priority": "high" if row.seq_tup_read > 10000 else "medium"
                })
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to generate index suggestions", error=str(e))
            return []


async def optimize_database() -> Dict[str, Any]:
    """Run database optimization commands."""
    results = {"optimizations": [], "errors": []}
    
    async with get_db_session() as session:
        try:
            if "postgresql" in settings.DATABASE_URL:
                # PostgreSQL optimizations
                optimizations = [
                    ("ANALYZE", "Update table statistics"),
                    ("VACUUM", "Reclaim storage and update statistics"),
                    ("REINDEX", "Rebuild indexes for better performance")
                ]
                
                for command, description in optimizations:
                    try:
                        await session.execute(text(command))
                        results["optimizations"].append({
                            "command": command,
                            "description": description,
                            "status": "success"
                        })
                    except Exception as e:
                        results["errors"].append({
                            "command": command,
                            "error": str(e)
                        })
                        
            else:
                # SQLite optimizations
                try:
                    await session.execute(text("VACUUM"))
                    await session.execute(text("ANALYZE"))
                    results["optimizations"].append({
                        "command": "VACUUM; ANALYZE",
                        "description": "Optimized SQLite database",
                        "status": "success"
                    })
                except Exception as e:
                    results["errors"].append({
                        "command": "VACUUM/ANALYZE",
                        "error": str(e)
                    })
            
            await session.commit()
            
        except Exception as e:
            logger.error("Database optimization failed", error=str(e))
            results["errors"].append({"general_error": str(e)})
    
    return results


async def get_database_health() -> Dict[str, Any]:
    """Get comprehensive database health metrics."""
    health = {
        "status": "healthy",
        "query_stats": query_stats,
        "slow_queries": await get_slow_queries(5),
        "connection_pool": {},
        "performance_issues": []
    }
    
    # Add connection pool info
    engine = get_engine()
    if hasattr(engine.pool, 'size'):
        health["connection_pool"] = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin(),
        }
    
    # Check for performance issues
    slow_queries = health["slow_queries"]
    if slow_queries and slow_queries[0]["avg_time"] > 2.0:
        health["performance_issues"].append("Slow queries detected (>2s average)")
        health["status"] = "warning"
    
    total_errors = sum(stats.get("errors", 0) for stats in query_stats.values())
    if total_errors > 10:
        health["performance_issues"].append(f"High error rate ({total_errors} total errors)")
        health["status"] = "warning"
    
    return health


# Decorator for automatic query profiling
def profile_query(query_name: str):
    """Decorator to automatically profile database queries."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Find session in arguments
            session = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break
            
            if not session:
                # No session found, call function normally
                return await func(*args, **kwargs)
            
            async with QueryProfiler(query_name, session):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator