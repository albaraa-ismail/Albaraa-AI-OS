import hashlib
import json
import threading
import time
from typing import Any, Optional

from core.core_ai import sb


class ForensicAuditLedger:
    def __init__(self) -> None:
        self._chain: list[dict[str, Any]] = []
        self._prev_hash = "0" * 64
        self._lock = threading.Lock()

    @staticmethod
    def _compute_hash(
        index: int, timestamp: float, actor: str, action: str, details_json: str, prev_hash: str
    ) -> str:
        raw = f"{index}|{timestamp:.6f}|{actor}|{action}|{details_json}|{prev_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append(self, actor: str, action: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        details = details or {}
        details_json = json.dumps(details, ensure_ascii=False, sort_keys=True)
        with self._lock:
            idx = (self._chain[-1]["index"] + 1) if self._chain else 1
            ts = time.time()
            block_hash = self._compute_hash(idx, ts, actor, action, details_json, self._prev_hash)
            entry = {
                "index": idx,
                "timestamp": ts,
                "actor": actor,
                "action": action,
                "details": details,
                "details_json": details_json,
                "prev_hash": self._prev_hash,
                "hash": block_hash,
            }
            self._chain.append(entry)
            self._prev_hash = block_hash
            if len(self._chain) > 500:
                self._chain.pop(0)

        threading.Thread(
            target=self._persist_async,
            args=(block_hash, actor, action, details_json),
            daemon=True,
        ).start()
        return entry

    @staticmethod
    def _persist_async(block_hash: str, actor: str, action: str, details_json: str) -> None:
        try:
            sb("POST", "self_learning_logs", {
                "user_role": "forensic_audit",
                "task_type": action,
                "lesson_learned": f"[{block_hash[:16]}] actor={actor} | {details_json[:180]}",
            })
        except Exception:
            pass

    def verify_integrity(self) -> dict[str, Any]:
        with self._lock:
            if not self._chain:
                return {"valid": True, "blocks_checked": 0}
            for i, curr in enumerate(self._chain):
                expected = self._compute_hash(
                    curr["index"],
                    curr["timestamp"],
                    curr["actor"],
                    curr["action"],
                    curr["details_json"],
                    curr["prev_hash"],
                )
                if curr["hash"] != expected:
                    return {"valid": False, "corrupted_at_index": curr["index"]}
                if i > 0 and curr["prev_hash"] != self._chain[i - 1]["hash"]:
                    return {"valid": False, "corrupted_at_index": curr["index"]}
            return {"valid": True, "blocks_checked": len(self._chain), "latest_hash": self._prev_hash}


AUDIT_LEDGER = ForensicAuditLedger()
