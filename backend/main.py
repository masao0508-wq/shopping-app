import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class MenuRequest(BaseModel):
    stock: list = []
    store: str = "ロピア"
    needs_lunch: list = []
    use_bento: bool = True

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 503回避のため、2.5より負荷が分散されている 2.0系Liteモデル を使用
    # これでも503が出る場合は 'gemini-1.5-flash' に戻すのも手です
    model_id = "gemini-2.0-flash-lite-preview-02-05"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # プロンプトはそのまま
    prompt_text = f"4人家族、1週間の献立表をJSONで作成。店:{req.store}、在庫:{', '.join(req.stock)}。必ず日本語で。"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            print(f"DEBUG: API Response Error: {res_data}")
            # 503の場合はユーザーに「混雑中」と伝える
            if response.status_code == 503:
                return {"error": "GoogleのAIが混雑しています。1分後に再度お試しください。"}
            return {"error": f"API Error {response.status_code}", "message": res_data.get("error", {}).get("message")}

        text = res_data['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"raw_text": text}

    except Exception as e:
        return {"error": "Internal Error", "message": str(e)}
