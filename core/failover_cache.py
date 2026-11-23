import re
import time
import hashlib
import threading
from typing import Any, Callable, Optional
from cachetools import TTLCache


class SmartSemanticCache:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 1500):
        self._cache: TTLCache = TTLCache(maxsize=max_items, ttl=ttl_seconds)
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, prompt: str, system: str = "", mode: str = "general") -> str:
        clean = lambda t: " ".join(re.sub(r"[\u064B-\u065F\u0670]", "", str(t or "")).split()).lower()
        raw = f"{mode}|{clean(system)}|{clean(prompt)}"
        return hashlib.blake2b(raw.encode("utf-8"), digest_size=20).hexdigest()

    def get(self, prompt: str, system: str = "", mode: str = "general") -> Optional[Any]:
        key = self._make_key(prompt, system, mode)
        with self._lock:
            val = self._cache.get(key)
            if val is not None:
                self.hits += 1
                return val
            self.misses += 1
            return None

    def set(self, prompt: str, value: Any, system: str = "", mode: str = "general") -> None:
        text = str(value or "").strip()
        if len(text) < 3 or "عذراً" in text or "تعذر" in text:
            return
        key = self._make_key(prompt, system, mode)
        with self._lock:
            self._cache[key] = value

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = max(self.hits + self.misses, 1)
            return {
                "cached_entries": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_pct": round((self.hits / total) * 100, 1),
            }


class CircuitBreakerFailover:
    def __init__(self, failure_threshold: int = 2, base_cooldown_sec: int = 90):
        self.threshold = failure_threshold
        self.base_cooldown = base_cooldown_sec
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}
        self._latencies: dict[str, float] = {}
        self._lock = threading.Lock()

    def _key_id(self, prov: Any) -> str:
        return f"{prov[0]}:{str(prov[1])[-6:]}" if isinstance(prov, tuple) and len(prov) == 2 else str(prov)

    def is_available(self, key_id: str) -> bool:
        with self._lock:
            if time.time() >= self._open_until.get(key_id, 0.0):
                self._open_until.pop(key_id, None)
                self._failures[key_id] = 0
                return True
            return False

    def record_success(self, key_id: str, latency_ms: float = 500.0) -> None:
        with self._lock:
            self._failures[key_id] = 0
            self._open_until.pop(key_id, None)
            prev = self._latencies.get(key_id, latency_ms)
            self._latencies[key_id] = round(prev * 0.65 + latency_ms * 0.35, 1)

    def record_failure(self, key_id: str) -> None:
        with self._lock:
            count = self._failures.get(key_id, 0) + 1
            self._failures[key_id] = count
            if count >= self.threshold:
                backoff = min(self.base_cooldown * (2 ** (count - self.threshold)), 600)
                self._open_until[key_id] = time.time() + backoff

    def execute_chain(self, providers: list[Any], runner: Callable[[Any], Optional[str]]) -> Optional[str]:
        if not providers:
            return None
        available = [p for p in providers if self.is_available(self._key_id(p))] or providers
        with self._lock:
            pool = sorted(available, key=lambda p: self._latencies.get(self._key_id(p), 800.0))

        for prov in pool:
            kid = self._key_id(prov)
            t0 = time.time()
            try:
                res = runner(prov)
                if res and isinstance(res, str) and len(res.strip()) > 1:
                    self.record_success(kid, (time.time() - t0) * 1000.0)
                    return res.strip()
            except Exception as exc:
                print(f"Failover Switch [{kid}]: {exc}", flush=True)
            self.record_failure(kid)
        return None


SMART_CACHE = SmartSemanticCache(ttl_seconds=3600, max_items=1500)
FAILOVER = CircuitBreakerFailover(failure_threshold=2, base_cooldown_sec=90)
