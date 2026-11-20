import re
import time
import hashlib
import threading
from typing import Any, Callable, Dict, Optional, Tuple
from cachetools import TTLCache


class SmartSemanticCache:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 1500):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._cache = TTLCache(maxsize=max_items, ttl=ttl_seconds)
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _normalize(self, txt: str) -> str:
        clean = re.sub(r'[\u064B-\u065F\u0670]', '', str(txt or ""))
        return " ".join(clean.split()).strip().lower()

    def _make_key(self, prompt: str, system: str = "", mode: str = "general") -> str:
        raw = f"{mode}|{self._normalize(system)}|{self._normalize(prompt)}"
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
    def set(self, prompt: str, value: Any, system: str = "", mode: str = "general"):
        if not value or "تعذر" in str(value) or (isinstance(value, str) and len(value.strip()) < 3):
            return
        key = self._make_key(prompt, system, mode)
        with self._lock:
            self._cache[key] = value

    def stats(self) -> Dict[str, Any]:
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
        self._failures: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}
        self._latencies: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _key_id(self, prov: Any) -> str:
        if isinstance(prov, tuple) and len(prov) == 2:
            return f"{prov[0]}:{str(prov[1])[-6:]}"
        return str(prov)

    def is_available(self, key_id: str) -> bool:
        with self._lock:
            until = self._open_until.get(key_id, 0.0)
            if time.time() >= until:
                if key_id in self._open_until:
                    del self._open_until[key_id]
                    self._failures[key_id] = 0
                return True
            return False

    def record_success(self, key_id: str, latency_ms: float = 500.0):
        with self._lock:
            self._failures[key_id] = 0
            self._open_until.pop(key_id, None)
            prev = self._latencies.get(key_id, latency_ms)
            self._latencies[key_id] = round((prev * 0.65) + (latency_ms * 0.35), 1)

    def record_failure(self, key_id: str):
        with self._lock:
            count = self._failures.get(key_id, 0) + 1
            self._failures[key_id] = count
            if count >= self.threshold:
                backoff = min(self.base_cooldown * (2 ** (count - self.threshold)), 600)
                self._open_until[key_id] = time.time() + backoff

    def execute_chain(self, providers: list, runner: Callable[[Any], Optional[str]]) -> Optional[str]:
        if not providers:
            return None

        available = [p for p in providers if self.is_available(self._key_id(p))]
        pool = available if available else providers

        with self._lock:
            pool = sorted(pool, key=lambda p: self._latencies.get(self._key_id(p), 800.0))

        for prov in pool:
            kid = self._key_id(prov)
            t0 = time.time()
            try:
                res = runner(prov)
                elapsed_ms = (time.time() - t0) * 1000.0
                if res and isinstance(res, str) and len(res.strip()) > 1:
                    self.record_success(kid, elapsed_ms)
                    return res.strip()
                self.record_failure(kid)
            except Exception as exc:
                print(f"Failover Switch [{kid}]: {exc}", flush=True)
                self.record_failure(kid)
        return None


SMART_CACHE = SmartSemanticCache(ttl_seconds=3600, max_items=1500)
FAILOVER = CircuitBreakerFailover(failure_threshold=2, base_cooldown_sec=90)
