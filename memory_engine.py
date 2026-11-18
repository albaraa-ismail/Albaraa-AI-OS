from core_ai import sb

def get_context(cid):
    hist = sb("GET", "self_learning_logs", q=f"?user_role=eq.{cid}&order=id.desc&limit=6")
    lessons = sb("GET", "self_learning_logs", q="?task_type=eq.خبرة_مكتسبة&order=id.desc&limit=5")
    h_txt = "\n".join([x.get("lesson_learned", "") for x in reversed(hist)])
    l_txt = "\n".join([x.get("lesson_learned", "") for x in lessons])
    return f"سياق المحادثة الأخيرة:\n{h_txt}\n\nخبرات النظام المتراكمة:\n{l_txt}"

def save_memory(cid, role, sname, msg, ans):
    sb("POST", "self_learning_logs", {"user_role": cid, "task_type": role, "lesson_learned": f"{sname}: {msg[:80]} -> الرد: {ans[:120]}"})
    if len(msg) > 25:
        sb("POST", "self_learning_logs", {"user_role": role, "task_type": "خبرة_مكتسبة", "lesson_learned": f"نمط عمل ({sname}): {msg[:100]}"})
