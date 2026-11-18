import os, time, threading
from datetime import datetime, timezone, timedelta
from evolution_engine import periodic_analytics, self_evolve_and_research

ADMIN_CID = os.environ.get("ADMIN_PHONE", "966575475336").strip() + "@c.us"
LAST_RUN = ""

def scheduler_loop():
    global LAST_RUN
    tz = timezone(timedelta(hours=3))
    while True:
        try:
            now = datetime.now(tz)
            today_key = now.strftime("%Y-%m-%d")
            # يوم الجمعة (weekday == 4) الساعة 10 صباحاً
            if now.weekday() == 4 and now.hour == 10 and LAST_RUN != today_key:
                LAST_RUN = today_key
                periodic_analytics(ADMIN_CID)
                self_evolve_and_research(ADMIN_CID)
        except Exception as e:
            print("Scheduler Err:", e)
        time.sleep(60)

def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()
