import os, time, threading
from datetime import datetime, timezone, timedelta
from core_ai import sb, send_msg
from evolution_engine import periodic_analytics, self_evolve_and_research, backup_memory

ADMIN_CID = os.environ.get("ADMIN_PHONE", "966575475336").strip() + "@c.us"
LAST_RUN = ""

def scheduler_loop():
    global LAST_RUN
    tz = timezone(timedelta(hours=3))
    while True:
        try:
            now = datetime.now(tz)
            now_hm, today = now.strftime("%Y-%m-%d %H:%M"), now.strftime("%Y-%m-%d")
            for r in sb("GET", "self_learning_logs", q="?task_type=eq.تذكير_نشط"):
                parts = r.get("lesson_learned", "").split("|", 1)
                if len(parts) == 2 and parts[0].strip() <= now_hm:
                    send_msg(r.get("user_role", ADMIN_CID), f"🔔 *تذكير بموعد/مهمة:*\n{parts[1]}")
                    sb("PATCH", "self_learning_logs", {"task_type": "تذكير_منتهي"}, q=f"?id=eq.{r['id']}")
            if now.weekday() == 4 and now.hour == 10 and LAST_RUN != today:
                LAST_RUN = today
                periodic_analytics(ADMIN_CID); self_evolve_and_research(ADMIN_CID)
                if now.day <= 7: backup_memory(ADMIN_CID)
        except Exception as e: print("Sched Err:", e)
        time.sleep(60)

def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()
