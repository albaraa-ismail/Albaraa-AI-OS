import re

DIALECT_MAP: dict[str, str] = {
    "ابغاء": "أريد",
    "ابغا": "أريد",
    "ابغى": "أريد",
    "ابي": "أريد",
    "أبي": "أريد",
    "وش": "ما هو",
    "ايش": "ماذا",
    "إيش": "ماذا",
    "سوي": "أنشئ",
    "سوّ": "أنشئ",
    "عطني": "أعطني",
    "اعطني": "أعطني",
    "الحين": "الآن",
    "عشان": "لكي",
    "حق": "الخاص بـ",
    "مره": "جداً",
    "مرة": "جداً",
    "كويس": "جيد",
    "تمام": "موافق",
}

_DIALECT_RE = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(k) for k in sorted(DIALECT_MAP, key=len, reverse=True)) + r")(?!\w)"
)

_ROBOTIC_OPENERS_RE = re.compile(
    r"^(?:بصفتي نموذج ذكاء اصطناعي|بصفتي ذكاءً اصطناعياً|بالتأكيد[!،]?\s*إليك|بالطبع[،!]?\s*يسعدني مساعدتك في|As an AI language model)[،:!.\-\s]*",
    re.IGNORECASE,
)


def normalize_arabic_dialect(text: str) -> str:
    """تطبيع اللهجة السعودية/العامية لتعزيز دقة الفهم مع الحفاظ على علامات الترقيم."""
    if not text:
        return text
    cleaned = re.sub(r"[ \t]+", " ", text).strip()
    return _DIALECT_RE.sub(lambda m: DIALECT_MAP[m.group(0)], cleaned)


def polish_human_style(text: str) -> str:
    """تحسين الصياغة البشرية وإزالة العبارات الآلية المكررة والحشو."""
    if not text:
        return text
    out = _ROBOTIC_OPENERS_RE.sub("", text.strip()).strip()
    return re.sub(r"\n{3,}", "\n\n", out)
