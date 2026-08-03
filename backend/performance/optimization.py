"""
Performance optimization utilities for LishFind application.

Includes query optimization, connection pooling, async processing, and resource management.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, Set
from concurrent.futures import ThreadPoolExecutor
import functools
from dataclasses import dataclass
import threading

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from core.config import settings

logger = structlog.get_logger(__name__)

# Global thread pool for CPU-bound operations
_thread_pool = None
_thread_pool_lock = threading.Lock()


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create thread pool for CPU-bound operations."""
    global _thread_pool
    if _thread_pool is None:
        with _thread_pool_lock:
            if _thread_pool is None:
                # Use number of CPU cores, but limit to avoid resource exhaustion
                max_workers = min(4, (settings.WORKER_PROCESSES or 1) * 2)
                _thread_pool = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="lishfind-worker"
                )
    return _thread_pool


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 100
    max_concurrent: int = 5
    delay_between_batches: float = 0.1


class BatchProcessor:
    """Efficient batch processing for database operations."""
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)
    
    async def process_batch(
        self,
        items: List[Any],
        processor: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """Process items in batches to optimize performance."""
        
        if not items:
            return []
        
        results = []
        total_items = len(items)
        
        logger.info("Starting batch processing", total_items=total_items, batch_size=self.config.batch_size)
        
        # Split items into batches
        batches = [
            items[i:i + self.config.batch_size]
            for i in range(0, total_items, self.config.batch_size)
        ]
        
        # Process batches with concurrency control
        async def process_single_batch(batch_items: List[Any]) -> List[Any]:
            async with self.semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor):
                        return await processor(batch_items, *args, **kwargs)
                    else:
                        # Run sync function in thread pool
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(
                            get_thread_pool(),
                            processor,
                            batch_items,
                            *args,
                            **kwargs
                        )
                except Exception as e:
                    logger.error("Batch processing failed", batch_size=len(batch_items), error=str(e))
                    return []
        
        # Process all batches concurrently
        batch_tasks = [process_single_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Collect results
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error("Batch failed with exception", error=str(batch_result))
            else:
                results.extend(batch_result)
            
            # Small delay between batches to prevent overwhelming the system
            if self.config.delay_between_batches > 0:
                await asyncio.sleep(self.config.delay_between_batches)
        
        logger.info("Batch processing completed", processed=len(results), expected=total_items)
        return results


class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    async def explain_query(session: AsyncSession, query: str, params: Dict = None) -> Dict[str, Any]:
        """Analyze query execution plan."""
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = await session.execute(text(explain_query), params or {})
            plan = result.fetchone()
            
            if plan and plan[0]:
                return {
                    "query": query,
                    "execution_plan": plan[0][0],
                    "analysis": QueryOptimizer._analyze_execution_plan(plan[0][0])
                }
        except Exception as e:
            logger.warning("Query analysis failed", query=query[:100], error=str(e))
        
        return {"query": query, "error": "Analysis failed"}
    
    @staticmethod
    def _analyze_execution_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze execution plan for performance issues."""
        analysis = {
            "total_cost": plan.get("Total Cost", 0),
            "execution_time": plan.get("Actual Total Time", 0),
            "rows_returned": plan.get("Actual Rows", 0),
            "issues": [],
            "recommendations": []
        }
        
        # Check for performance issues
        if analysis["execution_time"] > 1000:  # > 1 second
            analysis["issues"].append("Slow query execution")
            analysis["recommendations"].append("Consider adding indexes or optimizing query")
        
        if analysis["total_cost"] > 10000:
            analysis["issues"].append("High query cost")
            analysis["recommendations"].append("Review query structure and indexes")
        
        # Check for sequential scans
        def check_node(node):
            if node.get("Node Type") == "Seq Scan":
                table_name = node.get("Relation Name", "unknown")
                analysis["issues"].append(f"Sequential scan on table: {table_name}")
                analysis["recommendations"].append(f"Consider adding index for table: {table_name}")
            
            # Recursively check child nodes
            for child in node.get("Plans", []):
                check_node(child)
        
        check_node(plan)
        return analysis
    
    @staticmethod
    async def get_slow_queries(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries from pg_stat_statements."""
        try:
            query = """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements 
                WHERE calls > 10
                ORDER BY mean_time DESC 
                LIMIT :limit
            """
            
            result = await session.execute(text(query), {"limit": limit})
            return [dict(row) for row in result.fetchall()]
        
        except Exception as e:
            logger.warning("Failed to get slow queries", error=str(e))
            return []


class ConnectionPoolOptimizer:
    """Optimize database connection pool usage."""
    
    @staticmethod
    async def get_pool_stats() -> Dict[str, Any]:
        """Get connection pool statistics."""
        from database.connection import get_engine
        
        try:
            engine = get_engine()
            pool = engine.pool
            
            return {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
                "utilization": (pool.checkedout() / pool.size()) * 100 if pool.size() > 0 else 0,
                "recommendations": ConnectionPoolOptimizer._analyze_pool_usage(pool)
            }
        except Exception as e:
            logger.error("Failed to get pool stats", error=str(e))
            return {"error": str(e)}
    
    @staticmethod
    def _analyze_pool_usage(pool) -> List[str]:
        """Analyze pool usage and provide recommendations."""
        recommendations = []
        
        utilization = (pool.checkedout() / pool.size()) * 100 if pool.size() > 0 else 0
        
        if utilization > 90:
            recommendations.append("High pool utilization - consider increasing pool size")
        elif utilization < 20:
            recommendations.append("Low pool utilization - consider decreasing pool size")
        
        if pool.overflow() > pool.size() * 0.5:
            recommendations.append("High overflow usage - consider increasing base pool size")
        
        return recommendations


class AsyncProcessor:
    """Utilities for async processing and concurrency control."""
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks: Set[asyncio.Task] = set()
    
    async def run_concurrent(
        self,
        tasks: List[Callable],
        *args,
        **kwargs
    ) -> List[Any]:
        """Run multiple async tasks concurrently with limits."""
        
        async def run_task(task_func: Callable) -> Any:
            async with self.semaphore:
                try:
                    if asyncio.iscoroutinefunction(task_func):
                        return await task_func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(get_thread_pool(), task_func, *args, **kwargs)
                except Exception as e:
                    logger.error("Concurrent task failed", task=str(task_func), error=str(e))
                    return None
        
        # Create tasks
        concurrent_tasks = [asyncio.create_task(run_task(task)) for task in tasks]
        self.active_tasks.update(concurrent_tasks)
        
        try:
            # Wait for all tasks to complete
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]
        finally:
            # Clean up task references
            self.active_tasks.difference_update(concurrent_tasks)
    
    def schedule_background_task(self, coro) -> asyncio.Task:
        """Schedule a background task."""
        task = asyncio.create_task(coro)
        self.active_tasks.add(task)
        
        # Clean up when task completes
        task.add_done_callback(self.active_tasks.discard)
        return task
    
    async def cleanup(self):
        """Cancel all active tasks."""
        if self.active_tasks:
            logger.info("Cancelling background tasks", count=len(self.active_tasks))
            for task in self.active_tasks:
                task.cancel()
            
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            self.active_tasks.clear()


class MemoryOptimizer:
    """Memory usage optimization utilities."""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """Get current memory usage statistics."""
        try:
            import psutil
            import gc
            
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss": memory_info.rss,  # Physical memory
                "vms": memory_info.vms,  # Virtual memory
                "percent": process.memory_percent(),
                "gc_stats": {
                    "objects": len(gc.get_objects()),
                    "collections": gc.get_stats(),
                    "thresholds": gc.get_threshold()
                },
                "recommendations": MemoryOptimizer._analyze_memory_usage(process)
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _analyze_memory_usage(process) -> List[str]:
        """Analyze memory usage and provide recommendations."""
        recommendations = []
        
        try:
            memory_percent = process.memory_percent()
            
            if memory_percent > 80:
                recommendations.append("High memory usage - consider optimizing data structures")
            
            if memory_percent > 90:
                recommendations.append("Critical memory usage - immediate optimization needed")
            
        except Exception:
            pass
        
        return recommendations
    
    @staticmethod
    def optimize_gc():
        """Optimize garbage collection."""
        import gc
        
        # Force garbage collection
        collected = gc.collect()
        
        # Optimize GC thresholds for web applications
        gc.set_threshold(700, 10, 10)
        
        return {
            "collected_objects": collected,
            "new_thresholds": gc.get_threshold()
        }


# Decorators for performance optimization
def optimize_async(max_concurrent: int = 5):
    """Decorator to optimize async functions with concurrency control."""
    def decorator(func):
        semaphore = asyncio.Semaphore(max_concurrent)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with semaphore:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def cpu_bound(max_workers: int = None):
    """Decorator to run CPU-bound functions in thread pool."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=max_workers) if max_workers else get_thread_pool()
            return await loop.run_in_executor(executor, func, *args, **kwargs)
        return wrapper
    return decorator


def measure_performance(log_slow_threshold: float = 1.0):
    """Decorator to measure and log function performance."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > log_slow_threshold:
                    logger.warning(
                        "Slow function execution",
                        function=func.__name__,
                        duration=duration,
                        threshold=log_slow_threshold
                    )
                else:
                    logger.debug(
                        "Function execution",
                        function=func.__name__,
                        duration=duration
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Function execution failed",
                    function=func.__name__,
                    duration=duration,
                    error=str(e)
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > log_slow_threshold:
                    logger.warning(
                        "Slow function execution",
                        function=func.__name__,
                        duration=duration
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "Function execution failed",
                    function=func.__name__,
                    duration=duration,
                    error=str(e)
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global instances
batch_processor = BatchProcessor()
async_processor = AsyncProcessor()


# Utility functions
async def optimize_database_queries():
    """Run database optimization tasks."""
    async with get_db_session() as session:
        try:
            # Analyze slow queries
            slow_queries = await QueryOptimizer.get_slow_queries(session, limit=5)
            
            # Get pool statistics
            pool_stats = await ConnectionPoolOptimizer.get_pool_stats()
            
            # Log recommendations
            if slow_queries:
                logger.warning("Slow queries detected", count=len(slow_queries))
                for query in slow_queries[:3]:  # Log top 3
                    logger.info("Slow query", mean_time=query.get('mean_time'), calls=query.get('calls'))
            
            if pool_stats.get('recommendations'):
                for rec in pool_stats['recommendations']:
                    logger.info("Pool recommendation", recommendation=rec)
                    
        except Exception as e:
            logger.error("Database optimization check failed", error=str(e))


async def cleanup_resources():
    """Clean up resources and optimize memory."""
    try:
        # Clean up async processor
        await async_processor.cleanup()
        
        # Optimize garbage collection
        gc_stats = MemoryOptimizer.optimize_gc()
        logger.info("Memory optimization completed", **gc_stats)
        
        # Clean up thread pool
        global _thread_pool
        if _thread_pool:
            _thread_pool.shutdown(wait=False)
            _thread_pool = None
            
    except Exception as e:
        logger.error("Resource cleanup failed", error=str(e))