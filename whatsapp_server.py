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
<link href="https://googleapis.com" rel="stylesheet">
<style>
  :root {
    --bg: #0b1120;
    --card: #1e293b;
    --card-hover: #263349;
    --border: #334155;
    --primary: #10b981;
    --primary-dark: #059669;
    --accent: #3b82f6;
    --danger: #ef4444;
    --text: #f8fafc;
    --muted: #94a3b8;
  }
  * { box-sizing: border-box; font-family: 'Cairo', Tahoma, sans-serif; }
  body { background: var(--bg); color: var(--text); margin: 0; padding: 16px; line-height: 1.6; }
  .container { max-width: 1100px; margin: 0 auto; }
  
  /* الهيدر */
  .hero {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
  }
  .hero h1 { margin: 0; font-size: 22px; font-weight: 800; color: #fff; }
  .hero p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
  
  /* بطاقات الإحصائيات */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }
  .kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    transition: transform 0.2s;
  }
  .kpi-card:hover { transform: translateY(-2px); border-color: var(--primary); }
  .kpi-val { font-size: 26px; font-weight: 800; color: var(--primary); }
  .kpi-lbl { font-size: 12px; color: var(--muted); font-weight: 600; }

  /* شريط الأدوات */
  .toolbar {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .search-box {
    flex: 1;
    min-width: 220px;
    background: var(--card);
    border: 1px solid var(--border);
    color: #fff;
    padding: 11px 16px;
    border-radius: 12px;
    font-size: 14px;
    outline: none;
  }
  .search-box:focus { border-color: var(--accent); }
  .btn-add-open {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    color: #fff;
    border: none;
    padding: 11px 20px;
    border-radius: 12px;
    font-weight: 700;
    cursor: pointer;
    font-size: 14px;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  }

  /* نموذج الإضافة */
  .add-panel {
    display: none;
    background: var(--card);
    border: 1px solid var(--primary);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 22px;
  }
  .add-panel.open { display: block; animation: fadeIn 0.25s ease; }
  .fields-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 12px;
  }
  .field-group label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; font-weight: 600; }
  .field-group input {
    width: 100%;
    background: #0f172a;
    border: 1px solid var(--border);
    color: #fff;
    padding: 9px 12px;
    border-radius: 10px;
    font-size: 13px;
  }
  .field-group input:focus { border-color: var(--primary); outline: none; }

  /* شبكة البطاقات الاحترافية للسجلات */
  .records-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
    gap: 16px;
  }
  .rec-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    transition: all 0.2s;
    position: relative;
  }
  .rec-card:hover { border-color: #475569; box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
  .rec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 14px;
  }
  .rec-badge {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
  }
  .rec-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .rec-actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .btn-save {
    flex: 2;
    background: var(--accent);
    color: #fff;
    border: none;
    padding: 9px;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
    font-size: 13px;
  }
  .btn-save:hover { background: #2563eb; }
  .btn-del {
    flex: 1;
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 9px;
    border-radius: 10px;
    font-weight: 700;
    cursor: pointer;
    font-size: 13px;
  }
  .btn-del:hover { background: var(--danger); color: #fff; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
</style>
<script>
  function toggleAdd() {
    document.getElementById('addPanel').classList.toggle('open');
  }
  function filterCards(q) {
    q = q.toLowerCase();
    document.querySelectorAll('.rec-card').forEach(card => {
      let text = Array.from(card.querySelectorAll('input')).map(i => i.value.toLowerCase()).join(' ');
      card.style.display = text.includes(q) ? 'block' : 'none';
    });
  }
</script>
</head>
<body>
<div class="container">

  <div class="hero">
    <div>
      <h1>📊 {{ board.title }}</h1>
      <p>منصة إدارة حية وتفاعلية — جميع التعديلات تُحفظ مباشرة في السحابة</p>
    </div>
    <button class="btn-add-open" onclick="toggleAdd()">➕ إضافة سجل جديد</button>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-val">{{ board.rows|length }}</div>
      <div class="kpi-lbl">إجمالي السجلات</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val">{{ board.cols|length }}</div>
      <div class="kpi-lbl">مؤشرات التتبع</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-val" style="color:#60a5fa;">مباشر</div>
      <div class="kpi-lbl">حالة المزامنة</div>
    </div>
  </div>

  <div id="addPanel" class="add-panel">
    <h3 style="margin:0 0 8px; color:var(--primary);">✨ إضافة سجل جديد للوحة</h3>
    <form method="POST">
      <input type="hidden" name="action" value="add_row">
      <div class="fields-grid">
        {% for c in board.cols %}
        <div class="field-group">
          <label>{{ c }}</label>
          <input type="text" name="col_{{ loop.index0 }}" placeholder="أدخل {{ c }}..." required>
        </div>
        {% endfor %}
      </div>
      <div style="margin-top:15px; display:flex; gap:10px;">
        <button type="submit" class="btn-add-open">حفظ وإضافة السجل</button>
        <button type="button" class="btn-del" style="flex:0 0 100px;" onclick="toggleAdd()">إلغاء</button>
      </div>
    </form>
  </div>

  <div class="toolbar">
    <input type="text" class="search-box" onkeyup="filterCards(this.value)" placeholder="🔍 ابحث بالاسم، القسم، الرقم، أو أي معلومة...">
  </div>

  <div class="records-grid">
    {% for r in board.rows %}
    {% set r_idx = loop.index0 %}
    <div class="rec-card">
      <form method="POST">
        <input type="hidden" name="row_idx" value="{{ r_idx }}">
        <div class="rec-header">
          <span class="rec-badge">#{{ loop.index }}</span>
          <strong style="font-size:15px; color:#fff;">{{ r if r|length > 1 else r }}</strong>
        </div>
        <div class="rec-fields">
          {% for cell in r %}
          <div class="field-group">
            <label>{{ board.cols[loop.index0] if loop.index0 < board.cols|length else 'بيان' }}</label>
            <input type="text" name="col_{{ loop.index0 }}" value="{{ cell }}">
          </div>
          {% endfor %}
        </div>
        <div class="rec-actions">
          <button type="submit" name="action" value="save_row" class="btn-save">💾 حفظ التعديل</button>
          <button type="submit" name="action" value="del_row" class="btn-del">🗑️ حذف</button>
        </div>
      </form>
    </div>
    {% endfor %}
  </div>

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
<link href="https://googleapis.com" rel="stylesheet">
<style>
  * { box-sizing: border-box; font-family: 'Cairo', Tahoma, sans-serif; }
  body { background: #0b1120; color: #f8fafc; padding: 15px; margin: 0; }
  .header { background: linear-gradient(135deg, #1e293b, #0f172a); padding: 20px; border-radius: 16px; border: 1px solid #334155; margin-bottom: 20px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .stat-box { background: #1e293b; padding: 15px; border-radius: 14px; text-align: center; border: 1px solid #334155; }
  .stat-num { font-size: 24px; font-weight: 800; color: #10b981; }
  .tabs { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
  .tab-btn { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 10px 16px; border-radius: 10px; cursor: pointer; font-weight: 700; }
  .tab-btn.active { background: #10b981; color: #fff; border-color: #10b981; }
  .card { background: #1e293b; padding: 18px; border-radius: 16px; margin-bottom: 20px; border: 1px solid #334155; overflow-x: auto; }
  .section { display: none; }
  .section.active { display: block; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; min-width: 520px; }
  th, td { border: 1px solid #334155; padding: 10px; text-align: right; vertical-align: top; }
  th { background: #0f172a; color: #94a3b8; }
  input, textarea { width: 100%; background: #0f172a; color: #fff; border: 1px solid #475569; padding: 8px; border-radius: 8px; margin-bottom: 6px; }
  .btn { background: #10b981; color: #fff; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 700; margin: 2px; }
  .btn-warn { background: #f59e0b; }
  .btn-del { background: #ef4444; }
  .badge { padding: 3px 8px; border-radius: 6px; font-size: 12px; background: #334155; display: inline-block; margin-bottom: 5px; }
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
  <h2 style="margin:0;">⚡ لوحة القيادة الحية (تحكم مباشر)</h2>
  <p style="color:#94a3b8; margin:4px 0 0;">جميع التعديلات هنا تُحفظ فوراً وتنعكس مباشرة على عمل البوت في واتساب.</p>
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
          <td><span class="badge">{{ ag.unit_name }}</span><input type="text" name="agent_name" value="{{ ag.agent_name }}"></td>
          <td><textarea name="system_prompt" rows="3">{{ ag.system_prompt }}</textarea></td>
          <td>
            <button type="submit" name="action" value="edit_agent" class="btn">حفظ</button>
            {% if ag.unit_name == 'قيد_الاعتماد' %}<button type="submit" name="action" value="approve_agent" class="btn btn-warn">اعتماد</button>{% endif %}
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
      <tr><td>{{ k.deliverable_type }}</td><td>{{ k.response_time_sec }} ثانية</td><td>{{ k.user_growth_score }}%</td></tr>
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
    board = json.loads(rows_db.get("lesson_learned", "{}"))
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
