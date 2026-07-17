import time
import threading
from collections import deque

class TokenBucketThrottle:
    """
    Token Bucket algorithm for rate limiting.
    Allows for a burst of orders up to 'capacity', 
    refilling at 'fill_rate' tokens per second.
    """
    def __init__(self, capacity: int, fill_rate: float):
        """
        :param capacity: Maximum number of orders allowed in a burst.
        :param fill_rate: Rate at which orders are replenished per second.
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = float(capacity)
        self.last_fill_time = time.time()
        self.lock = threading.Lock()

    def allow_request(self, tokens: int = 1) -> bool:
        """
        Check if a request can proceed.
        :param tokens: Cost of the request (default 1).
        :return: True if allowed, False if throttled.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_fill_time
            
            # Refill tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
            self.last_fill_time = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter for strict rate limiting.
    Ensures that no more than 'max_requests' happen in 'time_window' seconds.
    """
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        with self.lock:
            now = time.time()
            # Remove timestamps older than the window
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False


class ThrottleEngine:
    """
    OMS Throttle Engine managing rate limits globally and per-entity (user/symbol).
    """
    def __init__(self):
        self.global_limiter = None
        self.entity_limiters = {}
        self.lock = threading.Lock()

    def set_global_limit(self, capacity: int, fill_rate: float):
        """Set a global token bucket throttle."""
        self.global_limiter = TokenBucketThrottle(capacity, fill_rate)

    def set_entity_limit(self, entity_id: str, max_requests: int, time_window: float):
        """Set a strict sliding window rate limit for a specific entity (e.g., user or symbol)."""
        with self.lock:
            self.entity_limiters[entity_id] = SlidingWindowRateLimiter(max_requests, time_window)

    def allow_order(self, entity_id: str = None) -> bool:
        """
        Evaluate if an order is allowed based on global and entity-specific limits.
        :param entity_id: Optional ID of the user or symbol to check specific limits.
        :return: True if the order should be sent, False if it should be rejected/queued.
        """
        # 1. Check global limits first
        if self.global_limiter and not self.global_limiter.allow_request():
            return False
            
        # 2. Check entity-specific limits
        if entity_id:
            with self.lock:
                entity_limiter = self.entity_limiters.get(entity_id)
            
            if entity_limiter and not entity_limiter.allow_request():
                return False

        return True
