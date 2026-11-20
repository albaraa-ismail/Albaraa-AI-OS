import math
import re
from collections import Counter
from typing import List, Dict
from core.core_ai import sb


def _ngrams(text: str, n: int = 3) -> Counter:
    clean = re.sub(r"\s+", " ", text.lower().strip())
    if len(clean) < n:
        return Counter([clean]) if clean else Counter()
    return Counter(clean[i : i + n] for i in range(len(clean) - n + 1))


def _cosine_sim(c1: Counter, c2: Counter) -> float:
    if not c1 or not c2:
        return 0.0
    common = set(c1.keys()) & set(c2.keys())
    dot = sum(c1[k] * c2[k] for k in common)
    norm1 = math.sqrt(sum(v * v for v in c1.values()))
    norm2 = math.sqrt(sum(v * v for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def hybrid_rank_memories(query: str, records: List[Dict], top_k: int = 5) -> List[str]:
    """بحث هجين يجمع بين التطابق اللفظي (Lexical) والتشابه الدلالي (Semantic N-gram Cosine)."""
    if not records:
        return []
    q_words = set(re.findall(r"[\w\u0600-\u06FF]+", query.lower()))
    q_vec = _ngrams(query)

    scored = []
    for rec in records:
        txt = str(rec.get("lesson_learned", "")).strip()
        if not txt or txt.startswith("{"):
            continue
        r_words = set(re.findall(r"[\w\u0600-\u06FF]+", txt.lower()))
        lexical = len(q_words & r_words) / max(len(q_words), 1)
        semantic = _cosine_sim(q_vec, _ngrams(txt))
        hybrid_score = (0.45 * lexical) + (0.55 * semantic)
        scored.append((hybrid_score, txt))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def get_context(cid: str, query: str = "") -> str:
    """استرجاع القواعد الدائمة + السياق الدلالي المرتبط بالطلب الحالي."""
    rules = sb("GET", "self_learning_logs", q="?user_role=eq.admin&is_active=eq.true&order=id.desc&limit=10")
    hist = sb("GET", "self_learning_logs", q=f"?user_role=eq.{cid}&order=id.desc&limit=15")

    lines = []
    if rules:
        active_rules = [r["lesson_learned"] for r in rules if r.get("lesson_learned") and not r["lesson_learned"].startswith("{")][:5]
        if active_rules:
            lines.append("📌 قواعد وتوجيهات دائمة من المشرف:\n- " + "\n- ".join(active_rules))

    if hist:
        if query:
            relevant = hybrid_rank_memories(query, hist, top_k=4)
        else:
            relevant = [h["lesson_learned"] for h in hist if h.get("lesson_learned") and not h["lesson_learned"].startswith("{")][:4]
        if relevant:
            lines.append("🧠 سياق المحادثات والذاكرة الدلالية السابقة:\n- " + "\n- ".join(relevant))

    return "\n\n".join(lines)


def save_memory(cid: str, role: str, sname: str, user_msg: str, ai_reply: str):
    """حفظ ملخص التفاعل في الذاكرة السحابية مع عزل بيانات كل مستفيد."""
    summary = f"[{sname}]: {user_msg[:140]} => {ai_reply[:180]}"
    sb("POST", "self_learning_logs", {
        "user_role": cid,
        "task_type": role,
        "lesson_learned": summary,
        "is_active": True,
    })
