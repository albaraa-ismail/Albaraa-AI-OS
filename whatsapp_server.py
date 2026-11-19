import os, json, threading
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

CUSTOM_BOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ board.title }}</title>
<style>
  body { font-family: Tahoma, sans-serif; background: #0f172a; color: #f8fafc; padding: 15px; margin: 0; }
  .header { background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
  .card { background: #1e293b; padding: 18px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; min-width: 500px; }
  th, td { border: 1px solid #334155; padding: 10px; text-align: right; }
  th { background: #0f172a; color: #10b981; }
  input { width: 92%; background: #0f172a; color: #fff; border: 1px solid #475569; padding: 8px; border-radius: 6px; }
  .btn { background: #10b981; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; }
  .btn-del { background: #ef4444; }
</style>
</head>
<body>
<div class="header">
  <h2>📊 {{ board.title }}</h2>
  <p style="color:#94a3b8; margin:0;">لوحة حية تفاعلية — عدّل أي خانة واضغط حفظ للتحديث الفوري.</p>
</div>

<div class="card">
  <h3>➕ إضافة سجل جديد</h3>
  <form method="POST">
    <input type="hidden" name="action" value="add_row">
    <table>
      <tr>
        {% for c in board.cols %}
        <td><input type="text" name="col_{{ loop.index0 }}" placeholder="{{ c }}" required></td>
        {% endfor %}
        <td><button type="submit" class="btn">إضافة</button></td>
      </tr>
    </table>
  </form>
</div>

<div class="card">
  <h3>📋 البيانات الحية</h3>
  <table>
    <tr>
      {% for c in board.cols %}<th>{{ c }}</th>{% endfor %}
      <th>تحكم</th>
    </tr>
    {% for r in board.rows %}
    {% set r_idx = loop.index0 %}
    <tr>
      <form method="POST">
        <input type="hidden" name="row_idx" value="{{ r_idx }}">
        {% for cell in r %}
        <td><input type="text" name="col_{{ loop.index0 }}" value="{{ cell }}"></td>
        {% endfor %}
        <td>
          <button type="submit" name="action" value="save_row" class="btn">حفظ</button>
          <button type="submit" name="action" value="del_row" class="btn btn-del">حذف</button>
        </td>
      </form>
    </tr>
    {% endfor %}
  </table>
</div>
</body>
</html>
"""

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
  table { width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 520px; }
  th, td { border: 1px solid #334155; padding: 10px; text-align: right; vertical-align: top; }
  th { background: #0f172a; color: #94a3b8; }
  input, textarea { width: 95%; background: #0f172a; color: #fff; border: 1px solid #475569; padding: 8px; border-radius: 6px; margin-bottom: 6px; }
  .btn { background: #10b981; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: bold; margin: 2px; }
  .btn-warn { background: #f59e0b; }
  .btn-del { background: #ef4444; }
  .badge { padding: 3px 8px; border-radius: 5px; font-size: 12px; background: #334155; display: inline-block; margin-bottom: 5px; }
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
  <div class="stat-box"><div class="stat-num">{{ active_count }}</div><div>الوكلاء النشطون</div></div>
  <div class="stat-box"><div class="stat-num">{{ kpis|length }}</div><div>المهام المنفذة</div></div>
  <div class="stat-box"><div class="stat-num">{{ avg_sec }} ث</div><div>متوسط الاستجابة</div></div>
  <div class="stat-box"><div class="stat-num">{{ total_saved }} د</div><div>الوقت الموفّر</div></div>
</div>
<div class="tabs">
  <button class="tab-btn active" onclick="showTab('agents-tab', this)">🤖 الوكلاء والأقسام</button>
  <button class="tab-btn" onclick="showTab('reminders-tab', this)">⏰ التذكيرات النشطة</button>
  <button class="tab-btn" onclick="showTab('kpis-tab', this)">📈 سجل الأداء المباشر</button>
</div>

<div id="agents-tab" class="section active">
  <div class="card">
    <h3>➕ إضافة قسم / وكيل جديد وتفعيله فوراً</h3>
    <form method="POST">
      <input type="hidden" name="action" value="add_agent">
      <input type="text" name="agent_name" placeholder="اسم الوكيل الجديد (مثلاً: خبير التسويق الرقمي)" required>
      <textarea name="system_prompt" rows="2" placeholder="اكتب مهام وصلاحيات الوكيل بدقة..." required></textarea>
      <button type="submit" class="btn">إضافة وتفعيل الوكيل</button>
    </form>
  </div>

  <div class="card">
    <h3>✏️ إدارة وتعديل الوكلاء</h3>
    <table>
      <tr><th>الوكيل والحالة</th><th>التعليمات (System Prompt)</th><th>تحكم</th></tr>
      {% for ag in agents %}
      <tr>
        <form method="POST">
          <input type="hidden" name="id" value="{{ ag.id }}">
          <td>
            <span class="badge">{{ ag.unit_name }}</span>
            <input type="text" name="agent_name" value="{{ ag.agent_name }}">
          </td>
          <td><textarea name="system_prompt" rows="3">{{ ag.system_prompt }}</textarea></td>
          <td>
            <button type="submit" name="action" value="edit_agent" class="btn">حفظ</button>
            {% if ag.unit_name == 'قيد_الاعتماد' %}
            <button type="submit" name="action" value="approve_agent" class="btn btn-warn">اعتماد</button>
            {% endif %}
            <button type="submit" name="action" value="del_agent" class="btn btn-del">حذف</button>
          </td>
        </form>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>

<div id="reminders-tab" class="section">
  <div class="card">
    <h3>⏰ التذكيرات النشطة المسجلة</h3>
    <table>
      <tr><th>موعد التنبيه</th><th>نص التذكير</th><th>إجراء</th></tr>
      {% for rem in reminders %}
      {% set parts = (rem.lesson_learned or '|').split('|', 1) %}
      <tr>
        <td>{{ parts }}</td>
        <td>{{ parts if parts|length > 1 else rem.lesson_learned }}</td>
        <td>
          <form method="POST" style="margin:0;">
            <input type="hidden" name="action" value="del_reminder">
            <input type="hidden" name="id" value="{{ rem.id }}">
            <button type="submit" class="btn btn-del">إلغاء وحذف</button>
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

@app.route("/board/<int:bid>", methods=["GET", "POST"])
def custom_board(bid):
    rows_db = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}") or []
    if not rows_db: return "اللوحة غير موجودة", 404
    board = json.loads(rows_db[0].get("lesson_learned", "{}"))
    if request.method == "POST":
        act = request.form.get("action")
        cols_len = len(board.get("cols", []))
        if act == "add_row":
            new_r = [request.form.get(f"col_{i}", "") for i in range(cols_len)]
            board.setdefault("rows", []).append(new_r)
        elif act == "save_row":
            idx = int(request.form.get("row_idx", 0))
            if 0 <= idx < len(board.get("rows", [])):
                board["rows"][idx] = [request.form.get(f"col_{i}", "") for i in range(cols_len)]
        elif act == "del_row":
            idx = int(request.form.get("row_idx", 0))
            if 0 <= idx < len(board.get("rows", [])):
                board["rows"].pop(idx)
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")
    return render_template_string(CUSTOM_BOARD_HTML, board=board)

@app.route("/dashboard/<cid>", methods=["GET", "POST"])
def live_dashboard(cid):
    if request.method == "POST":
        act = request.form.get("action")
        item_id = request.form.get("id")
        if act == "edit_agent":
            sb("PATCH", "agents_registry", {"agent_name": request.form.get("agent_name"), "system_prompt": request.form.get("system_prompt")}, q=f"?id=eq.{item_id}")
        elif act == "approve_agent":
            sb("PATCH", "agents_registry", {"unit_name": "قسم_معتمد_نشط"}, q=f"?id=eq.{item_id}")
        elif act == "del_agent":
            sb("PATCH", "agents_registry", {"unit_name": "محذوف"}, q=f"?id=eq.{item_id}")
        elif act == "add_agent":
            sb("POST", "agents_registry", {"unit_name": "قسم_معتمد_نشط", "agent_name": request.form.get("agent_name"), "sub_agents": "Admin Dashboard", "system_prompt": request.form.get("system_prompt")})
        elif act == "del_reminder":
            sb("DELETE", "self_learning_logs", q=f"?id=eq.{item_id}")

    agents = sb("GET", "agents_registry", q="?unit_name=neq.محذوف&order=id.desc&limit=30") or []
    active_count = sum(1 for a in agents if a.get("unit_name") == "قسم_معتمد_نشط")
    kpis = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=20") or []
    reminders = sb("GET", "self_learning_logs", q=f"?user_role=eq.{cid}&task_type=eq.تذكير_نشط&order=id.desc&limit=20") or []
    avg_sec = round(sum(float(x.get("response_time_sec", 0)) for x in kpis) / len(kpis), 1) if kpis else 0
    total_saved = sum(int(x.get("time_saved_min", 0)) for x in kpis)
    return render_template_string(FULL_DASHBOARD_HTML, agents=agents, active_count=active_count, kpis=kpis, reminders=reminders, avg_sec=avg_sec, total_saved=total_saved)

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
