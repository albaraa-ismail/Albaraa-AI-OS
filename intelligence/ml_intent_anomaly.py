import math
import re
from collections import Counter
from typing import Dict, Any


class MLIntentAndAnomalyEngine:
    """مصنف النوايا وكشف الشذوذ الإحصائي بتعلّم الآلة (Multinomial Likelihood + Z-Score)."""

    TRAINING_CORPUS = {
        "research": [
            "ابحث", "بحث", "معلومات", "مصادر", "مراجع", "تحليل", "مقارنة", "تقرير",
            "دراسة", "احصائيات", "إحصائيات", "اخبار", "أخبار", "تاريخ", "شرح", "فسر",
        ],
        "code": [
            "برمج", "كود", "بايثون", "python", "sql", "api", "خطأ", "bug", "دالة",
            "خوارزمية", "قاعدة بيانات", "سكريبت", "تطبيق", "موقع", "github", "html",
        ],
        "office": [
            "وورد", "word", "اكسل", "إكسل", "excel", "بوربوينت", "pptx", "باور بي",
            "power bi", "dax", "لوحة قيادة", "مؤشرات", "kpi", "رسم بياني", "عرض تقديمي",
        ],
        "voice": [
            "صوت", "بصمة صوتية", "اقرأ بصوت", "تسجيل صوتي", "نطق", "تحدث",
        ],
        "robotics": [
            "روبوت", "درون", "طائرة", "حساس", "أمر تحكم", "telemetry", "مسار", "حركة",
        ],
    }

    def __init__(self):
        self._lengths = [25, 40, 60, 80, 120, 180, 250]
        self._vocab = set(w for words in self.TRAINING_CORPUS.values() for w in words)

    def _tokenize(self, text: str):
        return re.findall(r"[\w\u0600-\u06FF]+", text.lower())

    def _compute_z_score(self, length: int) -> float:
        mean = sum(self._lengths) / len(self._lengths)
        variance = sum((x - mean) ** 2 for x in self._lengths) / max(len(self._lengths), 1)
        std = max(math.sqrt(variance), 15.0)
        z = abs(length - mean) / std
        if 5 <= length <= 1500:
            self._lengths.append(length)
            if len(self._lengths) > 200:
                self._lengths.pop(0)
        return round(z, 2)

    def predict(self, text: str) -> Dict[str, Any]:
        tokens = self._tokenize(text)
        token_counts = Counter(tokens)
        v_size = max(len(self._vocab), 1)

        scores = {}
        for intent, keywords in self.TRAINING_CORPUS.items():
            kw_set = set(keywords)
            log_prob = math.log(1.0 / len(self.TRAINING_CORPUS))
            hits = 0
            for tok, cnt in token_counts.items():
                if tok in kw_set or any(k in tok for k in kw_set if len(k) > 3):
                    hits += cnt
                    log_prob += cnt * math.log(2.0 / (len(keywords) + v_size))
                else:
                    log_prob += cnt * math.log(1.0 / (len(keywords) + v_size))
            scores[intent] = (hits, log_prob)

        best_intent = "general"
        best_hits = 0
        for intent, (hits, _) in scores.items():
            if hits > best_hits:
                best_hits = hits
                best_intent = intent

        z_score = self._compute_z_score(len(text))
        unique_ratio = len(set(text)) / max(len(text), 1)
        is_anomaly = (z_score > 4.5) or (len(text) > 30 and unique_ratio < 0.08)

        return {
            "intent": best_intent,
            "confidence": round(min(0.55 + (best_hits * 0.15), 0.98), 2),
            "is_anomaly": is_anomaly,
            "anomaly_score": z_score,
        }


INTENT_CLASSIFIER = MLIntentAndAnomalyEngine()
