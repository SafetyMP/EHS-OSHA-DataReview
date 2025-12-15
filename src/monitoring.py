"""
Monitoring and logging utilities.
"""

import logging
import time
from functools import wraps
from typing import Callable, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('osha_analyzer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def log_performance(func: Callable) -> Callable:
    """
    Decorator to log function execution time and errors.
    
    Usage:
        @log_performance
        def my_function():
            # ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func_name} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func_name} failed after {duration:.3f}s: {e}", exc_info=True)
            raise
    
    return wrapper


@contextmanager
def performance_timer(operation_name: str):
    """Context manager to time operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} took {duration:.3f}s")


class QueryCounter:
    """Simple counter for tracking database queries."""
    _count = 0
    _total_time = 0.0
    
    @classmethod
    def increment(cls, duration: float = 0.0):
        """Increment query count and add duration."""
        cls._count += 1
        cls._total_time += duration
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get query statistics."""
        avg_time = cls._total_time / cls._count if cls._count > 0 else 0
        return {
            "total_queries": cls._count,
            "total_time": round(cls._total_time, 3),
            "avg_time": round(avg_time, 3)
        }
    
    @classmethod
    def reset(cls):
        """Reset counters."""
        cls._count = 0
        cls._total_time = 0.0

