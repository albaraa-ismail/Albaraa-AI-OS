import math
import re
import threading
from collections import Counter
from typing import Any
from core.core_ai import sb

_AR_NORM = str.maketrans("أإآىة", "اائه")


def _norm(text: str) -> str:
    clean = re.sub(r"[\u064B-\u065F\u0670]", "", str(text or "").lower().translate(_AR_NORM))
    return re.sub(r"\s+", " ", clean).strip()


def _ngrams(text: str, n: int = 3) -> Counter:
    clean = _norm(text)
    return Counter([clean]) if 0 < len(clean) < n else Counter(clean[i : i + n] for i in range(len(clean) - n + 1))


def _cosine_sim(c1: Counter, c2: Counter) -> float:
    if not c1 or not c2:
        return 0.0
    dot = sum(c1[k] * c2[k] for k in (c1.keys() & c2.keys()))
    denom = math.sqrt(sum(v * v for v in c1.values())) * math.sqrt(sum(v * v for v in c2.values()))
    return dot / denom if denom else 0.0


def hybrid_rank_memories(query: str, records: list[dict[str, Any]], top_k: int = 5) -> list[str]:
    q_words = set(re.findall(r"[\w\u0600-\u06FF]+", _norm(query)))
    q_vec = _ngrams(query)
    scored: list[tuple[float, str]] = []

    for rec in records:
        if not isinstance(rec, dict):
            continue
        txt = str(rec.get("lesson_learned", "")).strip()
        if not txt or txt.startswith(("{", "<")):
            continue
        r_words = set(re.findall(r"[\w\u0600-\u06FF]+", _norm(txt)))
        lexical = len(q_words & r_words) / max(len(q_words), 1)
        semantic = _cosine_sim(q_vec, _ngrams(txt))
        scored.append(((0.45 * lexical) + (0.55 * semantic), txt))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def get_context(cid: str, query: str = "") -> str:
    rules = sb("GET", "self_learning_logs", q="?user_role=in.(admin,partner)&is_active=eq.true&order=id.desc&limit=10") or []
    hist = sb("GET", "self_learning_logs", q=f"?user_role=eq.mem:{cid}&order=id.desc&limit=15") or []

    lines: list[str] = []
    if isinstance(rules, list):
        active_rules = [
            r["lesson_learned"]
            for r in rules
            if isinstance(r, dict) and r.get("lesson_learned") and not str(r["lesson_learned"]).startswith(("{", "<"))
        ][:6]
        if active_rules:
            lines.append("📌 قواعد وتوجيهات دائمة:\n- " + "\n- ".join(active_rules))

    if isinstance(hist, list):
        relevant = (
            hybrid_rank_memories(query, hist, top_k=4)
            if query
            else [h["lesson_learned"] for h in hist if isinstance(h, dict) and h.get("lesson_learned") and not str(h["lesson_learned"]).startswith(("{", "<"))][:4]
        )
        if relevant:
            lines.append("🧠 سياق المحادثات السابقة:\n- " + "\n- ".join(relevant))

    return "\n\n".join(lines)


def save_memory(cid: str, role: str, sname: str, user_msg: str, ai_reply: str) -> None:
    payload = {
        "user_role": f"mem:{cid}",
        "task_type": role,
        "lesson_learned": f"[{sname}]: {user_msg[:140]} => {ai_reply[:180]}",
        "is_active": True,
    }
    threading.Thread(target=sb, args=("POST", "self_learning_logs", payload), daemon=True).start()
