"""
Retry logic with exponential backoff for handling failures.
"""
import time
import logging
from typing import Callable, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    RetryError
)
import requests

logger = logging.getLogger(__name__)


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception is retryable."""
    if isinstance(exception, requests.exceptions.RequestException):
        if isinstance(exception, requests.exceptions.HTTPError):
            status_code = exception.response.status_code if exception.response else None
            # Retry on 429 (rate limit) and 5xx (server errors)
            if status_code in [429, 500, 502, 503, 504]:
                return True
        # Retry on connection errors, timeouts
        return isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError
        ))
    return False


def retry_with_backoff(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(
                multiplier=initial_delay,
                max=max_delay,
                exp_base=exponential_base
            ),
            retry=retry_if_exception_type((
                requests.exceptions.RequestException,
            )),
            reraise=True
        )
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                if is_retryable_error(e):
                    logger.warning(
                        f"Retryable error in {func.__name__}: {e}. Retrying..."
                    )
                    raise
                else:
                    # Non-retryable error, don't retry
                    logger.error(
                        f"Non-retryable error in {func.__name__}: {e}"
                    )
                    raise
        
        return wrapper
    return decorator

