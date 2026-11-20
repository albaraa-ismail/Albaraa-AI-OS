import threading
import time
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger("AlbaraaEventBus")


class EventBus:
    """ناقل أحداث مركزي غير متزامن لربط وحدات النظام دون تشابك مباشر (Decoupled Architecture)."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable):
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Dict[str, Any], async_exec: bool = True):
        record = {
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload,
        }
        with self._lock:
            self._history.append(record)
            if len(self._history) > 200:
                self._history.pop(0)
            handlers = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))

        for handler in handlers:
            if async_exec:
                threading.Thread(target=self._safe_invoke, args=(handler, record), daemon=True).start()
            else:
                self._safe_invoke(handler, record)

    def _safe_invoke(self, handler: Callable, record: Dict[str, Any]):
        try:
            handler(record)
        except Exception as exc:
            logger.warning(f"EventBus handler error [{record['event']}]: {exc}")

    def recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])


BUS = EventBus()
