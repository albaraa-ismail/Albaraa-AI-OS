import traceback
from core_ai import send_msg

def safe_run(func, cid, msg, role, sname):
    try:
        func(cid, msg, role, sname)
    except Exception as e:
        full_err = traceback.format_exc()
        err = full_err.splitlines()[-1]
        print("GUARD CATCH:\n" + full_err, flush=True)
        send_msg(cid, f"⚠️ *تنبيه درع الحماية:*\nتعذر إكمال المهمة بسبب: `{err}`\nتم حماية النظام وجاهز لأمرك التالي.")
