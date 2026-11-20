import hashlib
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple


class SmartSemanticCache:
    """محرك تخزين مؤقت ذكي لتسريع الردود وتقليل استهلاك واجهات الذكاء الاصطناعي."""

    def __init__(self, ttl_seconds: int = 1800, max_items: int = 300):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, prompt: str, system: str = "", mode: str = "general") -> str:
        norm = f"{mode}|{' '.join(system.split())}|{' '.join(prompt.split())}"
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def get(self, prompt: str, system: str = "", mode: str = "general") -> Optional[Any]:
        key = self._make_key(prompt, system, mode)
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                self.misses += 1
                return None
            exp, val = item
            if now > exp:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return val

    def set(self, prompt: str, value: Any, system: str = "", mode: str = "general"):
        if not value or "تعذر" in str(value):
            return
        key = self._make_key(prompt, system, mode)
        with self._lock:
            if len(self._store) >= self.max_items:
                oldest = min(self._store.items(), key=lambda x: x[1][0])[0]
                del self._store[oldest]
            self._store[key] = (time.time() + self.ttl, value)

    def stats(self) -> Dict[str, Any]:
        total = max(self.hits + self.misses, 1)
        return {
            "cached_entries": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round((self.hits / total) * 100, 1),
        }


class CircuitBreakerFailover:
    """محرك التعافي من الأعطال والبدائل التلقائية (Circuit Breaker + Exponential Backoff)."""

    def __init__(self, failure_threshold: int = 3, cooldown_sec: int = 60):
        self.threshold = failure_threshold
        self.cooldown = cooldown_sec
        self._failures: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_available(self, provider: str) -> bool:
        with self._lock:
            until = self._open_until.get(provider, 0.0)
            if time.time() >= until:
                if provider in self._open_until:
                    del self._open_until[provider]
                    self._failures[provider] = 0
                return True
            return False

    def record_success(self, provider: str):
        with self._lock:
            self._failures[provider] = 0
            self._open_until.pop(provider, None)

    def record_failure(self, provider: str):
        with self._lock:
            count = self._failures.get(provider, 0) + 1
            self._failures[provider] = count
            if count >= self.threshold:
                self._open_until[provider] = time.time() + self.cooldown

    def execute_chain(self, providers: list, runner: Callable[[Any], Optional[str]]) -> Optional[str]:
        for prov in providers:
            name = prov[0] if isinstance(prov, tuple) else str(prov)
            if not self.is_available(name):
                continue
            try:
                res = runner(prov)
                if res:
                    self.record_success(name)
                    return res
                self.record_failure(name)
            except Exception:
                self.record_failure(name)
        return None


SMART_CACHE = SmartSemanticCache()
FAILOVER = CircuitBreakerFailover()
