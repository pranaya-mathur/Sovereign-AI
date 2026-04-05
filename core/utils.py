"""Common utilities for Sovereign AI."""

import threading
from typing import Callable, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    """Exception raised when a function execution times out."""
    pass

def run_with_timeout(func: Callable, args: Tuple = (), kwargs: Optional[dict] = None, timeout: float = 3.0) -> Any:
    """Run a function with timeout (works on Windows and Unix).
    
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
    
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        raise TimeoutException(f"Function timed out after {timeout} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]
