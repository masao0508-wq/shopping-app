@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 2.0系で最も標準的な名称に変更します。
    # もしこれでも 404 なら 'gemini-1.5-flash-8b' (超軽量版) を試します。
    model_id = "gemini-2.0-flash-exp" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    prompt_text = f"4人家族、1週間の献立表をJSONで作成。店:{req.store}、在庫:{', '.join(req.stock)}。必ず日本語で。"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            print(f"DEBUG: API Response Error: {res_data}")
            return {"error": f"API Error {response.status_code}", "message": res_data.get("error", {}).get("message")}

        text = res_data['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"raw_text": text}

    except Exception as e:
        return {"error": "Internal Error", "message": str(e)}
