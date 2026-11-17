# Albaraa-AI-OS
**Personal Multi-Agent AI Operating System**

نظام تشغيل شخصي يعتمد على معمارية تعدد الوكلاء (Multi-Agent Architecture) لأتمتة المهام، تنقيح البحث، وتطبيق قواعد الحوكمة على الأدوات والبيانات.

## هيكلية النظام (System Architecture)
يتكون النظام من وكيل رئيسي (Orchestrator) يدير 5 وكلاء متخصصين لضمان دقة التنفيذ وتقليل الأخطاء:

1. **Chief Agent (`chief_agent.py`)**: الوكيل القائد المسؤول عن استقبال الطلبات وتوزيع المهام.
2. **Research Agent (`research_agent.py`)**: وكيل البحث الذكي لتنقيح وتوسيع الاستعلامات بناءً على القيود.
3. **Governance Agent (`project_manager_agent.py`)**: وكيل الحوكمة والتشريعات لفحص النتائج واستبعاد الأدوات المخالفة للشروط.
4. **Builder Agent (`builder_agent.py`)**: وكيل التطوير لتوليد الهياكل البرمجية للمهام.
5. **Learning Agent (`learning_agent.py`)**: وكيل التقييم لقياس جودة ودقة المخرجات.
6. **Career Agent (`career_agent.py`)**: وكيل التصدير لإصدار التقارير النهائية وحفظها في الذاكرة.

## طريقة التشغيل (Deployment)
النظام مبني بلغة Python ويعمل كخادم ويب (Flask Webhook) متصل بواجهة واتساب عبر Green API:

```bash
pip install -r requirements.txt
gunicorn whatsapp_server:app
```

## متغيرات البيئة المطلوبة (Environment Variables)
* `GREEN_API_ID`: رقم المعرف الخاص بحساب Green API.
* `GREEN_API_TOKEN`: رمز الوصول (Token) الخاص بالربط.
