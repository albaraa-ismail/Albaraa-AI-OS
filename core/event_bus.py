import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger("AlbaraaEventBus")


class EventBus:
    def __init__(self, max_workers: int = 4) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="EventBus")

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict[str, Any], async_exec: bool = True) -> None:
        record = {"event": event_type, "timestamp": time.time(), "payload": payload}
        with self._lock:
            self._history.append(record)
            if len(self._history) > 200:
                self._history.pop(0)
            handlers = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))

        for handler in handlers:
            if async_exec:
                self._pool.submit(self._safe_invoke, handler, record)
            else:
                self._safe_invoke(handler, record)

    def _safe_invoke(self, handler: Callable[[dict[str, Any]], None], record: dict[str, Any]) -> None:
        try:
            handler(record)
        except Exception as exc:
            logger.warning("EventBus handler error [%s]: %s", record["event"], exc)

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])


BUS = EventBus()
