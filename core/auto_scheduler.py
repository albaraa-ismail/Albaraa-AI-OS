import os
import time
import threading
from datetime import datetime, timezone, timedelta
from core.core_ai import send_msg
from core.event_bus import BUS
from telemetry.evolution_engine import analyze_system_evolution, check_due_reminders

RIYADH_TZ = timezone(timedelta(hours=3))


def _scheduler_loop():
    admin_phone = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
    admin_cid = f"{admin_phone}@c.us" if admin_phone else ""
    last_daily_report = ""

    while True:
        try:
            now = datetime.now(RIYADH_TZ)
            # 1. فحص التذكيرات المستحقة كل دقيقة
            due_list = check_due_reminders()
            for item in due_list:
                target = item.get("cid") or admin_cid
                if target:
                    send_msg(target, f"⏰ *تذكير مجدول من Albaraa-AI-OS:*\n{item.get('text', '')}")
                    BUS.publish("scheduler.reminder_sent", {"cid": target})

            # 2. تقرير التطور الذاتي اليومي الساعة 09:00 صباحاً بتوقيت الرياض
            today_key = now.strftime("%Y-%m-%d")
            if now.hour == 9 and now.minute == 0 and last_daily_report != today_key:
                last_daily_report = today_key
                report = analyze_system_evolution()
                if admin_cid and report:
                    send_msg(admin_cid, report)
                    BUS.publish("scheduler.daily_report_sent", {"date": today_key})
        except Exception as exc:
            print(f"Scheduler Loop Err: {exc}", flush=True)

        time.sleep(55)


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    BUS.publish("scheduler.started", {"status": "active"})
    return t
