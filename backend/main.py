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
    # 最新モデル gemini-2.5-flash に合わせ、エンドポイントを v1beta に設定
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # 400エラーを回避するため、極めてシンプルなプロンプト構成にします
    prompt_text = f"4人家族、1週間の献立表をJSONで作成。店:{req.store}、在庫:{', '.join(req.stock)}。必ず日本語で。"
    
    # Google API が要求する最も基本的なペイロード構造
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ]
    }

    try:
        # ヘッダーではなくURLにキーを含める形式（最もエラーが出にくい）で試行
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            # Renderのログに詳細を出すためのプリント
            print(f"DEBUG: API Response Error: {res_data}")
            return {
                "error": f"API Error {response.status_code}",
                "message": res_data.get("error", {}).get("message", "Invalid Request"),
                "details": res_data.get("error", {}).get("status", "Unknown Status")
            }

        # テキスト抽出
        text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSONを抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"raw_text": text}

    except Exception as e:
        return {"error": "Internal Error", "message": str(e)}
