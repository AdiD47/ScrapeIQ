"""
Rate limiter to respect Jira API rate limits.
"""
import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Thread-safe rate limiter using token bucket algorithm."""
    
    def __init__(self, max_calls: int, period: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque() 
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        with self.lock:
            now = time.time()
            
            # Remove calls older than the period
            while self.calls and self.calls[0] < now - self.period:
                self.calls.popleft()
            
            # If we've hit the limit, wait until the oldest call expires
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Clean up again after sleeping
                    now = time.time()
                    while self.calls and self.calls[0] < now - self.period:
                        self.calls.popleft()
            
            # Record this call
            self.calls.append(time.time())

