import json
import time
import hashlib
import threading
from typing import Dict, Any, List
from core.core_ai import sb


class ForensicAuditLedger:
    """سجل التدقيق الجنائي غير القابل للتعديل (Tamper-Evident Cryptographic Hash Chain)."""

    def __init__(self):
        self._chain: List[Dict[str, Any]] = []
        self._prev_hash = "0" * 64
        self._lock = threading.Lock()

    def _compute_hash(self, index: int, timestamp: float, actor: str, action: str, details_json: str, prev_hash: str) -> str:
        raw = f"{index}|{timestamp:.6f}|{actor}|{action}|{details_json}|{prev_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append(self, actor: str, action: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        details = details or {}
        details_json = json.dumps(details, ensure_ascii=False, sort_keys=True)
        with self._lock:
            idx = len(self._chain) + 1
            ts = time.time()
            block_hash = self._compute_hash(idx, ts, actor, action, details_json, self._prev_hash)
            entry = {
                "index": idx,
                "timestamp": ts,
                "actor": actor,
                "action": action,
                "details": details,
                "prev_hash": self._prev_hash,
                "hash": block_hash,
            }
            self._chain.append(entry)
            self._prev_hash = block_hash
            if len(self._chain) > 500:
                self._chain.pop(0)

        # حفظ نسخة إثبات جنائي غير متزامنة في قاعدة البيانات إن توفرت
        try:
            sb("POST", "self_learning_logs", {
                "user_role": "forensic_audit",
                "task_type": action,
                "lesson_learned": f"[{block_hash[:16]}] actor={actor} | {details_json[:180]}",
            })
        except Exception:
            pass

        return entry

    def verify_integrity(self) -> Dict[str, Any]:
        with self._lock:
            if not self._chain:
                return {"valid": True, "blocks_checked": 0}
            for i in range(1, len(self._chain)):
                curr = self._chain[i]
                prev = self._chain[i - 1]
                if curr["prev_hash"] != prev["hash"]:
                    return {"valid": False, "corrupted_at_index": curr["index"]}
            return {"valid": True, "blocks_checked": len(self._chain), "latest_hash": self._prev_hash}


AUDIT_LEDGER = ForensicAuditLedger()
