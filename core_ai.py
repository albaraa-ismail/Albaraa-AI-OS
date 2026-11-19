def ai_ask(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    full_sys = (system_prompt + STRICT_POLICY).strip()
    safe_prompt = prompt[:28000]

    # 1. مزود Gemini المباشر
    if GEM_KEY:
        for model in ("gemini-3-flash-preview", "gemini-2.5-flash", "gemini-3.1-flash-lite-preview"):
            try:
                url = f"{GEMINI_BASE_URL}{model}:generateContent?key={GEM_KEY}"
                payload = {
                    "systemInstruction": {"parts": [{"text": full_sys}]},
                    "contents": [{"parts": [{"text": safe_prompt}]}],
                    "generationConfig": {"temperature": temperature}
                }
                r = requests.post(url, json=payload, timeout=35)
                if r.status_code == 200:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ Gemini ({model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ Gemini ({model}) Exc: {e}", flush=True)

    # 2. مزود Groq السريع
    if GROQ_KEY:
        for g_model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": full_sys}, {"role": "user", "content": safe_prompt}],
                    "temperature": temperature
                }
                r = requests.post(_GROQ_URL, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"].strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ Groq ({g_model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ Groq ({g_model}) Exc: {e}", flush=True)

    # 3. مزود OpenRouter الاحتياطي
    if OR_KEY:
        for or_model in ("google/gemini-3-flash-preview", "meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"):
            try:
                headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": or_model,
                    "messages": [{"role": "system", "content": full_sys}, {"role": "user", "content": safe_prompt}],
                    "temperature": temperature
                }
                r = requests.post(_OR_URL, headers=headers, json=payload, timeout=45)
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"].strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ OpenRouter ({or_model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ OpenRouter ({or_model}) Exc: {e}", flush=True)

    return "⚠ تعذر الحصول على استجابة من محركات الذكاء الاصطناعي حالياً، يرجى المحاولة بعد قليل."

def ai_ask_json(prompt: str, system_prompt: str = "") -> dict:
    sys_j = system_prompt + "\nأرجع كائن JSON صالح فقط بدون أي نص إضافي أو علامات markdown."
    raw = ai_ask(prompt, sys_j, temperature=0.1)
    if "{" in raw and "}" in raw:
        try:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception as e:
            print(f"JSON Parse Err: {e}", flush=True)
    return {}
