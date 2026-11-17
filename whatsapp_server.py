import os, requests, json, time, threading, openpyxl
from pptx import Presentation
from pptx.util import Pt
from docx import Document
from docx.shared import Pt as DocPt
from duckduckgo_search import DDGS
from flask import Flask, request, jsonify

app = Flask(__name__)
SEEN = set()

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def sb(method, table, payload=None, q=""):
    if not SB_URL or not SB_KEY:
        return list()
    url = f"{SB_URL}/rest/v1/{table}{q}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        r = requests.get(url, headers=h, timeout=12) if method == "GET" else requests.post(url, json=payload, headers=h, timeout=12)
        if r.status_code in (200, 201):
            return r.json()
    except Exception:
        pass
    return list()

def ai_ask(prompt, sys_role):
    if GROQ_KEY:
        try:
            r = requests.post(
                "https://groq.com",
                json={"model": "llama-3.3-70b-versatile", "messages": ({"role": "system", "content": sys_role}, {"role": "user", "content": prompt}), "temperature": 0.4},
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                timeout=35
            )
            if r.status_code == 200:
                txt = r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
                if txt:
                    return txt
        except Exception as e:
            print("Groq:", e, flush=True)

    if GEM_KEY:
        try:
            r = requests.post(
                f"https://googleapis.com{GEM_KEY}",
                json={"contents": ({"parts": ({"text": f"{sys_role}\n\n{prompt}"},)},)},
                timeout=35
            )
            if r.status_code == 200:
                c = r.json().get("candidates", list())
                if c:
                    txt = c.pop(0).get("content", {}).get("parts", list()).pop(0).get("text", "").strip()
                    if txt:
                        return txt
        except Exception as e:
            print("Gemini:", e, flush=True)

    if OR_KEY:
        try:
            r = requests.post(
                "https://openrouter.ai",
                json={"model": "openrouter/free", "messages": ({"role": "system", "content": sys_role}, {"role": "user", "content": prompt})},
                headers={"Authorization": f"Bearer {OR_KEY}"},
                timeout=35
            )
            if r.status_code == 200:
                txt = r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
                if txt:
                    return txt
        except Exception as e:
            print("OR:", e, flush=True)

    return ""

def send_msg(cid, txt):
    if not txt:
        return
    requests.post(f"https://greenapi.com{G_ID}/sendMessage/{G_TOK}", json={"chatId": cid, "message": txt}, timeout=20)

def send_file(cid, path, name, mime, cap):
    with open(path, "rb") as f:
        requests.post(f"https://greenapi.com{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": cid, "caption": cap}, files={"file": (name, f, mime)}, timeout=40)

def safe_json(raw):
    try:
        if "{" in raw and "}" in raw:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception:
        pass
    return None

def run_task(cid, msg, role, sname):
    t0 = time.time()
    low = msg.lower()

    if role == "admin" and msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        raw = ai_ask(msg, 'أعد JSON فقط: {"unit": "الوحدة", "name": "الاسم", "subs": "3 مساعدين", "prompt": "التعليمات"}')
        ag = safe_json(raw) or {"unit": "وحدة تخصصية", "name": msg[:30], "subs": "3 مساعدين تنفيذيين", "prompt": msg}
        sb("POST", "agents_registry", {"unit_name": ag.get("unit"), "agent_name": ag.get("name"), "sub_agents": ag.get("subs"), "system_prompt": ag.get("prompt")})
        send_msg(cid, f"🧬 *مصنع الوكلاء (Albaraa Ai os):*\nتم بناء وتفعيل الوكيل *{ag.get('name')}* في الذاكرة السحابية بنجاح!")
        return

    if role == "admin" and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        logs = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=100")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.sheet_view.rightToLeft = True
        ws.append(("رقم العملية", "المستخدم", "الوحدة المنفذة", "زمن الاستجابة (ث)", "الوقت الموفر (دقيقة)", "مؤشر تطور المستخدم", "نوع المخرج"))
        for i in logs:
            ws.append((i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")))
        wb.save("/tmp/KPI.xlsx")
        send_file(cid, "/tmp/KPI.xlsx", "Albaraa_KPIs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 جدول القياس وتطور المستخدم | Albaraa Ai os")
        return

    dtype = "استشارة وبناء هندسي"
    if any(k in low for k in ("وورد", "word", "docx", "تقرير رسمي", "خطاب")):
        send_msg(cid, "⏳ جاري صياغة وتنسيق مستند الوورد الرسمي عبر مجلس الوكلاء...")
        sys_doc = (
            "أنت كبير المستشارين التنفيذيين في منظومة Albaraa Ai os. "
            "اكتب تقريراً رسمياً متكاملاً، مفصلاً، ومنظماً بأعلى مستوى لغوي وهندسي باللغة العربية. "
            "قسّم التقرير إلى: الملخص التنفيذي، البنية المعمارية للنظام، المزايا التنافسية، مؤشرات الأداء والجدوى، والخاتمة والتوصيات. "
            "اجعل كل قسم غنياً بالتفاصيل العملية."
        )
        raw = ai_ask(msg, sys_doc)
        doc = Document()
        doc.add_heading("تقرير تنفيذي رسمي — منظومة Albaraa Ai os", 0)
        doc.add_paragraph("إعداد: فريق الهندسة والذكاء الاصطناعي المؤسسي")
        doc.add_paragraph("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for line in raw.split("\n"):
            clean_l = line.strip().replace("**", "")
            if not clean_l:
                continue
            if clean_l.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً", "1.", "2.", "3.", "4.", "5.")):
                doc.add_heading(clean_l.lstrip("# "), level=1)
            else:
                p = doc.add_paragraph(clean_l)
                p.style.font.size = DocPt(12)
        doc.save("/tmp/Doc.docx")
        send_file(cid, "/tmp/Doc.docx", "Albaraa_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 مستند وورد رسمي متكامل | Albaraa Ai os")
        dtype = "Word"

    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):
        send_msg(cid, "⏳ جاري بناء وتنسيق ملف الإكسل الاحترافي...")
        sys_xl = (
            "أنت كبير مهندسي البيانات في Albaraa Ai os. صمم جدول بيانات احترافي متكامل. "
            'أعد JSON فقط بهذا الشكل الدقيق: {"title": "عنوان الجدول", "rows": (("العمود 1", "العمود 2", "العمود 3"), ("قيمة 1", "قيمة 2", "قيمة 3"))}'
        )
        raw = ai_ask(msg, sys_xl)
        d = safe_json(raw)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.sheet_view.rightToLeft = True
        if d and d.get("rows"):
            for r in d.get("rows"):
                ws.append(list(r))
        else:
            ws.append(("البند", "التفاصيل والبيانات الهندسية"))
            for idx, line in enumerate(raw.split("\n"), 1):
                if line.strip():
                    ws.append((f"بند {idx}", line.strip().replace("**", "")))
        wb.save("/tmp/Out.xlsx")
        send_file(cid, "/tmp/Out.xlsx", "Albaraa_Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف إكسل احترافي جاهز | Albaraa Ai os")
        dtype = "Excel"

    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح", "pptx")):
        send_msg(cid, "⏳ جاري تصميم العرض التقديمي التنفيذي...")
        sys_pp = (
            "أنت مدير العروض التنفيذية في Albaraa Ai os. صمم عرضاً تقديمياً احترافياً من 6 شرائح غنية بالمحتوى. "
            "اكتب عنوان كل شريحة في سطر، وتحته 4 نقاط قوية ومفيدة، وافصل بين كل شريحة والتي تليها بسطر فارغ."
        )
        raw = ai_ask(msg, sys_pp)
        prs = Presentation()
        s0 = prs.slides.add_slide(prs.slide_layouts.pop(0))
        s0.shapes.title.text = "عرض استراتيجي — منظومة Albaraa Ai os"
        s0.placeholders.pop(1).text = msg[:70]
        chunks = tuple(x.strip() for x in raw.split("\n\n") if x.strip())
        for block in chunks[:7]:
            lines = tuple(l.strip().replace("**", "") for l in block.split("\n") if l.strip())
            if not lines:
                continue
            sl = prs.slides.add_slide(prs.slide_layouts.pop(1))
            sl.shapes.title.text = lines.pop(0).lstrip("# ")[:65]
            tf = sl.placeholders.pop(1).text_frame
            tf.clear()
            for idx, pt in enumerate(lines):
                p = tf.paragraphs.pop(0) if idx == 0 else tf.add_paragraph()
                p.text = f"• {pt.lstrip('•-* ')}"
                p.font.size = Pt(18)
        prs.save("/tmp/Out.pptx")
        send_file(cid, "/tmp/Out.pptx", "Albaraa_Slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ عرض تقديمي احترافي جاهز | Albaraa Ai os")
        dtype = "PowerPoint"

    else:
        web = ""
        try:
            with DDGS() as dd:
                web = "\n".join(tuple(f"- {x.get('title', '')}: {x.get('body', '')}" for x in dd.text(msg, max_results=3)))
        except Exception:
            pass
        ags = sb("GET", "agents_registry", q="?order=id.desc&limit=15")
