"""
LLM Response Cache — avoids re-invoking the LLM for identical prompt pairs.

Uses SHA-256 of (system_prompt + user_prompt + model) as cache key.
In-memory LRU with configurable max size.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_MAX_CACHE_SIZE = int(__import__("os").getenv("EMBEDFORGE_CACHE_SIZE", "100"))


@dataclass
class CacheEntry:
    response: str
    timestamp: float
    hit_count: int = 0


class LLMCache:
    """Thread-safe LRU cache for LLM responses keyed by prompt hash."""

    def __init__(self, max_size: int = _MAX_CACHE_SIZE) -> None:
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(system_prompt: str, user_prompt: str, model: str = "") -> str:
        raw = f"{model}::{system_prompt}::{user_prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, system_prompt: str, user_prompt: str, model: str = "") -> Optional[str]:
        key = self._make_key(system_prompt, user_prompt, model)
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                self._hits += 1
                entry.hit_count += 1
                self._cache.move_to_end(key)
                logger.debug("Cache HIT: key=%s hits=%d", key[:12], entry.hit_count)
                return entry.response
            self._misses += 1
            return None

    def put(self, system_prompt: str, user_prompt: str, response: str, model: str = "") -> None:
        key = self._make_key(system_prompt, user_prompt, model)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key].response = response
                return
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = CacheEntry(response=response, timestamp=time.time())

    def invalidate(self, system_prompt: str, user_prompt: str, model: str = "") -> None:
        key = self._make_key(system_prompt, user_prompt, model)
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
            }


# Singleton
llm_cache = LLMCache()
