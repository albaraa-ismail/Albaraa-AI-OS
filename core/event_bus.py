import time
import logging
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger("AlbaraaEventBus")


class EventBus:
    def __init__(self, max_workers: int = 4) -> None:
        self._subs: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)
        self._history: deque[dict[str, Any]] = deque(maxlen=200)
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="EventBus")

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            if handler not in self._subs[event_type]:
                self._subs[event_type].append(handler)

    def publish(self, event_type: str, payload: dict[str, Any], async_exec: bool = True) -> None:
        record = {"event": event_type, "timestamp": time.time(), "payload": payload}
        with self._lock:
            self._history.append(record)
            handlers = self._subs.get(event_type, []) + self._subs.get("*", [])

        for handler in handlers:
            if async_exec:
                self._pool.submit(self._invoke, handler, record)
            else:
                self._invoke(handler, record)

    emit = publish

    def _invoke(self, handler: Callable[[dict[str, Any]], None], record: dict[str, Any]) -> None:
        try:
            handler(record)
        except Exception as exc:
            logger.warning("EventBus error [%s]: %s", record["event"], exc)

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)[-limit:]


BUS = EventBus()
