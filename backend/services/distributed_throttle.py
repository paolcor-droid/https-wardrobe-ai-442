"""Shared MongoDB rate limiter for login and recovery across API workers.

Atomic $inc per identity and fixed time window. Fail closed on DB errors.
Caller should hash identifiers to avoid storing raw email or IP in counters.
"""
import hashlib
import os
import time
from datetime import datetime, timezone, timedelta

class MongoRateLimiter:
    def __init__(self, collection, namespace, attempts, window, clock=None):
        self.collection = collection
        self.namespace = namespace
        self.attempts = attempts
        self.window = window
        self.clock = clock or time.time

    def _key(self, identifier):
        period = int(self.clock() // self.window)
        digest = hashlib.sha256((self.namespace + ":" + identifier).encode()).hexdigest()
        return f"{self.namespace}:{digest}:{period}"

    async def check_and_count(self, identifier):
        now = self.clock()
        key = self._key(identifier)
        expires = datetime.fromtimestamp((int(now // self.window) + 2) * self.window, tz=timezone.utc)
        # One atomic increment: no two workers can both bypass a fixed threshold.
        result = await self.collection.find_one_and_update(
            {"_id": key},
            {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": expires}},
            upsert=True, return_document=True,
        )
        return result["count"] <= self.attempts

async def allow_attempt(limiter, identifier):
    return await limiter.check_and_count(identifier)
