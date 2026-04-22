"""
Helper functions for MDVRP solvers
"""

import time
from typing import Optional


def seconds(val: float) -> float:
    """
    Identity function for code clarity.

    Args:
        val: Value in seconds

    Returns:
        Same value (seconds)

    Example:
        >>> seconds(60)
        60
        >>> time_limit = seconds(30)
    """
    return val


def minutes(val: float) -> float:
    """
    Convert minutes to seconds.

    Args:
        val: Value in minutes

    Returns:
        Value in seconds

    Example:
        >>> minutes(5)
        300
        >>> time_limit = minutes(10)  # 10 minutes = 600 seconds
    """
    return val * 60


def hours(val: float) -> float:
    """
    Convert hours to seconds.

    Args:
        val: Value in hours

    Returns:
        Value in seconds

    Example:
        >>> hours(1)
        3600
        >>> time_limit = hours(2)  # 2 hours = 7200 seconds
    """
    return val * 3600


class TimeLimiter:
    """
    Context manager for time limiting operations.

    Example:
        >>> with TimeLimiter(seconds(5)) as limiter:
        ...     while not limiter.is_exceeded():
        ...         # Do work
        ...         pass
    """

    def __init__(self, timeout: Optional[float] = None):
        """
        Initialize time limiter.

        Args:
            timeout: Timeout in seconds. None means no limit.
        """
        self.timeout = timeout
        self.start_time = None

    def __enter__(self):
        """Start timing when entering context."""
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        """Exit context (cleanup if needed)."""
        pass

    def is_exceeded(self) -> bool:
        """
        Check if time limit has been exceeded.

        Returns:
            True if timeout exceeded, False otherwise.
            If timeout is None, always returns False.
        """
        if self.timeout is None:
            return False
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) > self.timeout

    def elapsed(self) -> float:
        """
        Get elapsed time since start.

        Returns:
            Elapsed time in seconds.
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
