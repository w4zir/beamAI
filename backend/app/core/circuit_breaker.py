"""
Circuit breaker pattern implementation for external dependencies.

Per ARCHITECTURE.md:
- Failure threshold: 50% error rate over 1 minute
- Open duration: 30 seconds
- Half-open: Test with 10% traffic
"""
import time
import asyncio
from enum import Enum
from typing import Optional, Callable, Any
from collections import deque
from threading import Lock
from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, bypass service
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker implementation for external dependencies.
    
    Configuration:
    - failure_threshold: 50% error rate over time_window_seconds
    - open_duration_seconds: 30 seconds
    - half_open_test_percentage: 10% of requests
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,  # 50% error rate
        time_window_seconds: int = 60,  # 1 minute
        open_duration_seconds: int = 30,  # 30 seconds
        half_open_test_percentage: float = 0.1,  # 10% of requests
        min_requests_for_threshold: int = 10,  # Minimum requests to calculate error rate
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.time_window_seconds = time_window_seconds
        self.open_duration_seconds = open_duration_seconds
        self.half_open_test_percentage = half_open_test_percentage
        self.min_requests_for_threshold = min_requests_for_threshold
        
        self._state = CircuitState.CLOSED
        self._lock = Lock()
        self._request_history: deque = deque()  # (timestamp, success: bool)
        self._opened_at: Optional[float] = None
        self._half_open_test_count = 0
        self._half_open_success_count = 0
        self._half_open_failure_count = 0
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        with self._lock:
            self._update_state()
            return self._state
    
    def _update_state(self) -> None:
        """Update circuit breaker state based on current conditions."""
        now = time.time()
        
        # Clean old requests outside time window
        cutoff_time = now - self.time_window_seconds
        while self._request_history and self._request_history[0][0] < cutoff_time:
            self._request_history.popleft()
        
        if self._state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self._opened_at and (now - self._opened_at) >= self.open_duration_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_test_count = 0
                self._half_open_success_count = 0
                self._half_open_failure_count = 0
                logger.info(
                    "circuit_breaker_half_open",
                    circuit_breaker=self.name,
                    state="half_open",
                )
        
        elif self._state == CircuitState.HALF_OPEN:
            # In half-open, we test with a percentage of requests
            # State will be updated after each request based on results
            pass
        
        elif self._state == CircuitState.CLOSED:
            # Check if we should open the circuit
            if len(self._request_history) >= self.min_requests_for_threshold:
                failures = sum(1 for _, success in self._request_history if not success)
                total = len(self._request_history)
                error_rate = failures / total if total > 0 else 0.0
                
                if error_rate >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = now
                    logger.warning(
                        "circuit_breaker_opened",
                        circuit_breaker=self.name,
                        error_rate=error_rate,
                        failures=failures,
                        total=total,
                    )
    
    def _should_test_half_open(self) -> bool:
        """Determine if this request should test the half-open circuit."""
        if self._state != CircuitState.HALF_OPEN:
            return False
        
        # Test with percentage of requests
        self._half_open_test_count += 1
        should_test = (self._half_open_test_count % int(1 / self.half_open_test_percentage)) == 0
        return should_test
    
    def _record_result(self, success: bool) -> None:
        """Record a request result."""
        now = time.time()
        
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                if success:
                    self._half_open_success_count += 1
                else:
                    self._half_open_failure_count += 1
                
                # If we have enough test results, decide on state
                total_tests = self._half_open_success_count + self._half_open_failure_count
                if total_tests >= 5:  # Test with at least 5 requests
                    if self._half_open_success_count >= 3:  # 60% success rate
                        # Close the circuit
                        self._state = CircuitState.CLOSED
                        self._opened_at = None
                        logger.info(
                            "circuit_breaker_closed",
                            circuit_breaker=self.name,
                            success_count=self._half_open_success_count,
                            failure_count=self._half_open_failure_count,
                        )
                    else:
                        # Reopen the circuit
                        self._state = CircuitState.OPEN
                        self._opened_at = now
                        logger.warning(
                            "circuit_breaker_reopened",
                            circuit_breaker=self.name,
                            success_count=self._half_open_success_count,
                            failure_count=self._half_open_failure_count,
                        )
            else:
                # Record in history for closed state
                self._request_history.append((now, success))
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection (sync).
        
        Returns:
            Function result if circuit is closed or half-open test passes
            Raises CircuitBreakerOpenError if circuit is open
        """
        state = self.state
        
        if state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is OPEN. Service unavailable."
            )
        
        if state == CircuitState.HALF_OPEN:
            if not self._should_test_half_open():
                # Skip this request (90% of requests in half-open)
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is HALF_OPEN. Skipping test request."
                )
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_result(True)
            return result
        except Exception as e:
            self._record_result(False)
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with circuit breaker protection.
        
        Returns:
            Function result if circuit is closed or half-open test passes
            Raises CircuitBreakerOpenError if circuit is open
        """
        state = self.state
        
        if state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is OPEN. Service unavailable."
            )
        
        if state == CircuitState.HALF_OPEN:
            if not self._should_test_half_open():
                # Skip this request (90% of requests in half-open)
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is HALF_OPEN. Skipping test request."
                )
        
        # Execute the async function
        try:
            result = await func(*args, **kwargs)
            self._record_result(True)
            return result
        except Exception as e:
            self._record_result(False)
            raise
    
    def get_metrics(self) -> dict:
        """Get circuit breaker metrics for monitoring."""
        with self._lock:
            self._update_state()
            
            now = time.time()
            cutoff_time = now - self.time_window_seconds
            recent_requests = [
                (ts, success) for ts, success in self._request_history
                if ts >= cutoff_time
            ]
            
            failures = sum(1 for _, success in recent_requests if not success)
            total = len(recent_requests)
            error_rate = failures / total if total > 0 else 0.0
            
            return {
                "name": self.name,
                "state": self._state.value,
                "recent_requests": total,
                "recent_failures": failures,
                "error_rate": error_rate,
                "opened_at": self._opened_at,
                "half_open_tests": self._half_open_test_count,
                "half_open_successes": self._half_open_success_count,
                "half_open_failures": self._half_open_failure_count,
            }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass

