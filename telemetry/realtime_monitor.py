import time
import threading
from collections import defaultdict
from typing import Dict, Any
from core.failover_cache import SMART_CACHE


class RealtimeAgentMonitor:
    """نظام الرصد والتتبع اللحظي لأداء الوكلاء وزمن الاستجابة ومعدل النجاح."""

    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "success": 0, "failures": 0, "total_sec": 0.0, "active": 0}
        )
        self._start_time = time.time()
        self._lock = threading.Lock()

    def record_start(self, agent_name: str):
        with self._lock:
            self._stats[agent_name]["calls"] += 1
            self._stats[agent_name]["active"] += 1

    def record_end(self, agent_name: str, elapsed_sec: float, success: bool = True):
        with self._lock:
            st = self._stats[agent_name]
            st["active"] = max(0, st["active"] - 1)
            st["total_sec"] += elapsed_sec
            if success:
                st["success"] += 1
            else:
                st["failures"] += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            agents_view = {}
            for name, st in self._stats.items():
                done = max(st["success"] + st["failures"], 1)
                agents_view[name] = {
                    "calls": st["calls"],
                    "active": st["active"],
                    "success_rate_pct": round((st["success"] / done) * 100, 1),
                    "avg_latency_sec": round(st["total_sec"] / done, 2),
                }
        return {
            "uptime_sec": round(time.time() - self._start_time, 1),
            "cache": SMART_CACHE.stats(),
            "agents": agents_view,
        }


MONITOR = RealtimeAgentMonitor()
