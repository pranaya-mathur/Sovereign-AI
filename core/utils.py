"""Common utilities for Sovereign AI."""

import asyncio
from typing import Callable, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    """Exception raised when a function execution times out."""
    pass

def run_with_timeout(func: Callable, args: Tuple = (), kwargs: Optional[dict] = None, timeout: float = 3.0) -> Any:
    """Run a function with timeout using asyncio cancellation semantics.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments  
        timeout: Timeout in seconds
        
    Returns:
        Function result or raises TimeoutException
    """
    if kwargs is None:
        kwargs = {}
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        raise TimeoutException("run_with_timeout cannot be called from an active event loop")

    return asyncio.run(_run_with_timeout_async(func, args, kwargs, timeout))


async def _run_with_timeout_async(
    func: Callable,
    args: Tuple,
    kwargs: dict,
    timeout: float,
) -> Any:
    try:
        async with asyncio.timeout(timeout):
            task = asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))
            return await task
    except TimeoutError as exc:
        raise TimeoutException(f"Function timed out after {timeout} seconds") from exc
