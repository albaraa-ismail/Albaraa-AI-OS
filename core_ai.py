def ai_ask(p, s):
    clean_s, err = s + POLICY, "لا توجد مفاتيح"
    if GROQ_KEY:
        u_g = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
        for gm in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"):
            try:
                r = requests.post(u_g, json={"model": gm, "messages": [{"role": "system", "content": clean_s}, {"role": "user", "content": p}], "temperature": 0.4}, headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=22)
                if r.status_code == 200:
                    choices = r.json().get("choices", [])
                    if choices:
                        txt = choices.pop(0).get("message", {}).get("content", "").strip()
                        if txt and not _is_refusal(txt): return txt
                err = f"Groq({gm}):{r.status_code}"
                print("AI WARN:", err, flush=True)
            except Exception as e:
                err = f"GroqEx:{str(e)[:25]}"
                print("AI WARN:", err, flush=True)
    if GEM_KEY:
        b_gem = base64.b64decode("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy8=").decode()
        for gem in ("gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"):
            try:
                r = requests.post(f"{b_gem}{gem}:generateContent?key={GEM_KEY}", json={"contents": [{"parts": [{"text": f"{clean_s}\n\n{p}"}]}]}, timeout=25)
                if r.status_code == 200:
                    cands = r.json().get("candidates", [])
                    if cands:
                        parts = cands.pop(0).get("content", {}).get("parts", [])
                        if parts:
                            txt = parts.pop(0).get("text", "").strip()
                            if txt and not _is_refusal(txt): return txt
                err = f"Gem({gem}):{r.status_code}"
                print("AI WARN:", err, flush=True)
            except Exception as e:
                err = f"GemEx:{str(e)[:25]}"
                print("AI WARN:", err, flush=True)
    return f"⚠️ تعذر التوليد ({err})"
