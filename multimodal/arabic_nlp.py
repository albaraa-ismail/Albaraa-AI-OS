import re

DIALECT_MAP = {
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


def normalize_arabic_dialect(text: str) -> str:
    """تطبيع اللهجة السعودية/العامية وتصحيح الهمزات الشائعة لتعزيز دقة الفهم."""
    if not text:
        return text
    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split(" ")
    normalized = []
    for w in words:
        stripped = w.strip("؟?!.,،:")
        if stripped in DIALECT_MAP:
            normalized.append(w.replace(stripped, DIALECT_MAP[stripped]))
        else:
            normalized.append(w)
    return " ".join(normalized)


def polish_human_style(text: str) -> str:
    """تحسين الصياغة البشرية وإزالة العبارات الآلية المكررة والحشو."""
    if not text:
        return text
    robotic_openers = [
        "بصفتي نموذج ذكاء اصطناعي،",
        "بصفتي ذكاءً اصطناعياً،",
        "بالتأكيد! إليك",
        "بالطبع، يسعدني مساعدتك في",
        "As an AI language model,",
    ]
    out = text.strip()
    for opener in robotic_openers:
        if out.startswith(opener):
            out = out[len(opener):].strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out
