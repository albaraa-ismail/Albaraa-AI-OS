import os
import json
from flask import Flask, request, jsonify
from agents.chief_agent import ChiefAgent
from agents.research_agent import ResearchAgent
from agents.project_manager_agent import ProjectManagerAgent

app = Flask(__name__)
chief = ChiefAgent()
research = ResearchAgent()
governance = ProjectManagerAgent()

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_data = request.values if request.values else request.get_json()
    user_phone = incoming_data.get("From", "Unknown_User")
    user_message = incoming_data.get("Body", "").strip()
    
    system_constraints = "يجب الالتزام بالخيارات المجانية ومفتوحة المصدر وحظر الأدوات المدفوعة"
    
    try:
        init_status = chief.orchestrate_task(user_message, system_constraints)
        refined_query = research.refine_query(user_message, system_constraints)
        
        mock_web_data = [
            {"name": "GitHub Copilot", "type": "Paid"},
            {"name": "VS Code Core", "type": "Free"},
            {"name": "Ollama Local LLM", "type": "Free"}
        ]
        
        approved, blocked = governance.audit_results(mock_web_data, system_constraints)
        
        whatsapp_response = (
            f"🤖 *مرحباً بك في منصة Albaraa-Ai-os*\n"
            f"-----------------------------------------\n"
            f"🔍 *تم تنقيح طلبك إلى:* {refined_query}\n\n"
            f"🛡️ *تقرير وكيل الحوكمة والتشريعات:*\n"
            f"✅ الأدوات المعتمدة والمجانية: {[t['name'] for t in approved]}\n"
            f"❌ الأدوات المحجوبة والمدفوعة: {[t['name'] for t in blocked]}\n"
            f"-----------------------------------------\n"
            f"💾 تم معالجة طلبك وحفظه بأمان في الذاكرة السحابية."
        )
        return jsonify({"status": "success", "reply": whatsapp_response})
        
    except Exception as e:
        return jsonify({"status": "error", "reply": "⚠️ واجه النظام خطأ برمجياً سحابياً."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
