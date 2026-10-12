"""Conservative process-local development login throttle.

This is supplemental protection, NOT a distributed production rate limiter.
Public deployment remains gated until shared-store throttling is installed.
"""
from collections import deque
from threading import Lock
from time import monotonic

class LoginThrottle:
    def __init__(self, attempts=5, window=300):
        self.attempts = attempts
        self.window = window
        self.events = {}
        self.lock = Lock()

    def is_blocked(self, key):
        now = monotonic()
        with self.lock:
            events = self.events.setdefault(key, deque())
            while events and events[0] <= now - self.window:
                events.popleft()
            return len(events) >= self.attempts

    def fail(self, key):
        now = monotonic()
        with self.lock:
            events = self.events.setdefault(key, deque())
            while events and events[0] <= now - self.window:
                events.popleft()
            events.append(now)

    def clear(self, key):
        with self.lock:
            self.events.pop(key, None)
