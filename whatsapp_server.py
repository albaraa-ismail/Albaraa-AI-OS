import os, threading
from flask import Flask, request, jsonify, render_template_string
from agent_brain import run_task
from safe_guard import safe_run
from auto_scheduler import start_scheduler
from media_reader import analyze_media
from core_ai import sb

app = Flask(__name__)
start_scheduler()
SEEN = set()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()
ALLOWED_GROUPS = [g.strip() for g in os.environ.get("ALLOWED_GROUP", "120363413772983962@g.us").split(",") if "@g.us" in g]

FULL_DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>مركز القيادة والتحكم الحي</title>
<style>
  body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 15px; margin: 0; }
  .header { background: linear-gradient(135deg, #1e293b, #0f172a); padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .stat-box { background: #1e293b; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #334155; }
  .stat-num { font-size: 24px; font-weight: bold; color: #10b981; }
  .tabs { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
  .tab-btn { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: bold; }
  .tab-btn.active { background: #10b981; color: #fff; border-color: #10b981; }
  .card { background: #1e293b; padding: 18px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; overflow-x: auto; }
  .section { display: none; }
  .section.active { display: block; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 500px; }
  th, td { border: 1px solid #334155; padding: 10px; text-align: right; }
  th { background: #0f172a; color: #94a3b8; }
  input, textarea { width: 95%; background: #0f172a; color: #fff; border: 1px solid #475569; padding: 8px; border-radius: 6px; margin-bottom: 8px; }
  .btn { background: #10b981; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; }
  .btn-del { background: #ef4444; }
</style>
<script>
  function showTab(tabId, btn) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
  }
</script>
</head>
<body>

<div class="header">
  <h2>⚡ لوحة القيادة الحية (تحكم مباشر)</h2>
  <p style="color:#94a3b8; margin:0;">جميع التعديلات هنا تُحفظ فوراً وتنعكس مباشرة على عمل البوت في واتساب.</p>
</div>

<div class="stats">
  <div class="stat-box"><div class="stat-num">{{ agents|length }}</div><div>الوكلاء النشطون</div></div>
  <div class="stat-box"><div class="stat-num">{{ kpis|length }}</div><div>المهام المنفذة</div></div>
  <div class="stat-box"><div class="stat-num">{{ avg_sec }} ث</div><div>متوسط الاستجابة</div></div>
  <div class="stat-box"><div class="stat-num">{{ total_saved }} د</div><div>الوقت الموفّر</div></div>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="showTab('agents-tab', this)">🤖 الوكلاء (تعديل/إضافة)</button>
  <button class="tab-btn" onclick="showTab('reminders-tab', this)">⏰ التذكيرات والمهام</button>
  <button class="tab-btn" onclick="showTab('kpis-tab', this)">📈 سجل الأداء المباشر</button>
</div>

<div id="agents-tab" class="section active">
  <div class="card">
    <h3>➕ إضافة وكيل جديد فوراً</h3>
    <form method="POST">
      <input type="hidden" name="action" value="add_agent">
      <input type="text" name="agent_name" placeholder="اسم الوكيل الجديد (مثلاً: خبير التسويق)" required>
      <textarea name="system_prompt" rows="2" placeholder="اكتب تعليمات الوكيل ودوره بدقة..." required></textarea>
      <button type="submit" class="btn">إضافة وتفعيل الوكيل</button>
    </form>
  </div>
  <div class="card">
    <h3>✏️ تعديل الوكلاء الحاليين</h3>
    <table>
      <tr><th>اسم الوكيل</th><th>التعليمات (System Prompt)</th><th>تحكم</th></tr>
      {% for ag in agents %}
      <tr>
        <form method="POST">
          <input type="hidden" name="action" value="edit_agent">
          <input type="hidden" name="id" value="{{ ag.id }}">
          <td><input type="text" name="agent_name" value="{{ ag.agent_name }}"></td>
          <td><textarea name="system_prompt" rows="2">{{ ag.system_prompt }}</textarea></td>
          <td><button type="submit" class="btn">حفظ</button></td>
        </form>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>

<div id="reminders-tab" class="section">
  <div class="card">
    <h3>⏰ التذكيرات والمواعيد المسجلة</h3>
    <table>
      <tr><th>التذكير / المهمة</th><th>الوقت / الحالة</th><th>إجراء</th></tr>
      {% for rem in reminders %}
      <tr>
        <td>{{ rem.reminder_text or rem.task or rem.content or 'مهمة مسجلة' }}</td>
        <td>{{ rem.remind_at or rem.status or 'نشط' }}</td>
        <td>
          <form method="POST" style="margin:0;">
            <input type="hidden" name="action" value="del_reminder">
            <input type="hidden" name="id" value="{{ rem.id }}">
            <button type="submit" class="btn btn-del">حذف</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>

<div id="kpis-tab" class="section">
  <div class="card">
    <h3>📈 آخر العمليات المنجزة</h3>
    <table>
      <tr><th>نوع المخرج</th><th>زمن التنفيذ</th><th>نقاط النمو</th></tr>
      {% for k in kpis %}
      <tr>
        <td>{{ k.deliverable_type }}</td>
        <td>{{ k.response_time_sec }} ثانية</td>
        <td>{{ k.user_growth_score }}%</td>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>

</body>
</html>
"""

@app.route("/dashboard/<cid>", methods=["GET", "POST"])
def live_dashboard(cid):
    if request.method == "POST":
        act = request.form.get("action")
        if act == "edit_agent":
            sb("PATCH", "agents_registry", {
                "agent_name": request.form.get("agent_name"),
                "system_prompt": request.form.get("system_prompt")
            }, q=f"?id=eq.{request.form.get('id')}")
        elif act == "add_agent":
            sb("POST", "agents_registry", {
                "unit_name": "قسم_معتمد_نشط",
                "agent_name": request.form.get("agent_name"),
                "system_prompt": request.form.get("system_prompt")
            })
        elif act == "del_reminder":
            sb("DELETE", "reminders", q=f"?id=eq.{request.form.get('id')}")

    agents = sb("GET", "agents_registry", q="?order=id.desc&limit=30") or []
    kpis = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=20") or []
    reminders = sb("GET", "reminders", q=f"?user_id=eq.{cid}&order=id.desc&limit=20") or []

    avg_sec = round(sum(float(x.get("response_time_sec", 0)) for x in kpis) / len(kpis), 1) if kpis else 0
    total_saved = sum(int(x.get("time_saved_min", 0)) for x in kpis)

    return render_template_string(
        FULL_DASHBOARD_HTML,
        agents=agents, kpis=kpis, reminders=reminders,
        avg_sec=avg_sec, total_saved=total_saved
    )

def process_incoming(cid, msg, m_url, m_mime, role, sname):
    final_msg = analyze_media(m_url, m_mime, msg) if m_url else msg
    if final_msg: safe_run(run_task, cid, final_msg, role, sname)

@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return jsonify({"status": "online"}), 200
    d = request.get_json(silent=True) or {}
    wt = d.get("typeWebhook", "")
    sd, md = d.get("senderData", {}), d.get("messageData", {})
    cid, sender, sname = sd.get("chatId", "").strip(), sd.get("sender", ""), sd.get("senderName", "User")
    f_data = md.get("fileMessageData") or md.get("audioMessageData") or md.get("imageMessageData") or md.get("documentMessageData") or {}
    msg = (md.get("textMessageData", {}).get("textMessage", "") or md.get("extendedTextMessageData", {}).get("text", "") or f_data.get("caption", "")).strip()
    m_url, m_mime = f_data.get("downloadUrl", ""), f_data.get("mimeType", "audio/ogg")
    print(f"IN: {wt} | CID: {cid} | URL: {bool(m_url)} | MSG: {msg[:15]}")
    if not cid or (not msg and not m_url) or msg.startswith(("🤖", "⏳", "🎬", "🧬", "📊", "📄", "📽️", "⚠️", "🔐", "✅", "🚀", "📈", "🛠️", "🔔", "⏰", "💾", "📋", "🗑️")): return jsonify({"status": "ignore"}), 200
    mid = d.get("idMessage", "")
    if mid and mid in SEEN: return jsonify({"status": "dup"}), 200
    if mid: SEEN.add(mid)
    is_out = "outgoing" in wt
    is_admin = is_out or (ADMIN_PHONE in (sender or cid))
    if not (("@c.us" in cid and ADMIN_PHONE in cid) or (cid in ALLOWED_GROUPS)):
        return jsonify({"status": "blocked"}), 200
    role = "admin" if is_admin else "co_lead"
    threading.Thread(target=process_incoming, args=(cid, msg, m_url, m_mime, role, sname)).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
