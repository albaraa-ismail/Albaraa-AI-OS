import traceback
from core_ai import send_msg

def safe_run(func, cid, msg, role, sname):
    try:
        func(cid, msg, role, sname)
    except Exception as e:
        err = traceback.format_exc().splitlines()[-1]
        print("GUARD CATCH:", err)
        send_msg(cid, f"⚠️ *تنبيه درع الحماية:*\nتعذر إكمال المهمة بسبب: `{err}`\nتم حماية النظام وجاهز لأمرك التالي.")
