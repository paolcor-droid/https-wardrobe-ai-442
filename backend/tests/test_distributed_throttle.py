"""Mongo shared rate limiting tests with atomic update simulation."""
import asyncio
import threading
from datetime import datetime, timezone

import pytest

from services.distributed_throttle import MongoRateLimiter


class AtomicCollection:
    def __init__(self):
        self.lock = threading.Lock()
        self.docs = {}

    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        assert upsert and return_document is True
        assert "$inc" in update and "$setOnInsert" in update
        with self.lock:
            k = query["_id"]
            if k not in self.docs:
                self.docs[k] = {"count": 0, **update["$setOnInsert"]}
            self.docs[k]["count"] += update["$inc"]["count"]
            return dict(self.docs[k])


@pytest.mark.asyncio
async def test_shared_login_limit_across_workers():
    storage = AtomicCollection()
    first = MongoRateLimiter(storage, "login", 5, 300, clock=lambda: 1000)
    second = MongoRateLimiter(storage, "login", 5, 300, clock=lambda: 1000)
    results = await asyncio.gather(*(limiter.check_and_count("same-ip:same-email")
                                     for limiter in [first, second, first, second, first, second]))
    assert results == [True, True, True, True, True, False]
    assert len(storage.docs) == 1
    k = next(iter(storage.docs))
    assert "same-email" not in k
    assert storage.docs[k]["expires_at"] > datetime.fromtimestamp(1000, tz=timezone.utc)


@pytest.mark.asyncio
async def test_distinct_keys_and_fixed_window_rollover():
    storage = AtomicCollection()
    now = [1000]
    limiter = MongoRateLimiter(storage, "recovery", 1, 3600, clock=lambda: now[0])
    assert await limiter.check_and_count("account-a")
    assert not await limiter.check_and_count("account-a")
    assert await limiter.check_and_count("account-b")
    now[0] = 3601
    assert await limiter.check_and_count("account-a")


@pytest.mark.asyncio
async def test_backend_storage_errors_are_not_silently_permitted():
    class Failing:
        async def find_one_and_update(self, *args, **kwargs):
            raise RuntimeError("storage failed")
    limiter = MongoRateLimiter(Failing(), "login", 5, 300)
    with pytest.raises(RuntimeError, match="storage failed"):
        await limiter.check_and_count("some-user")
