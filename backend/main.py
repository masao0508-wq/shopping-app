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
   # ここを Lite に変更
    model_id = "gemini-2.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # プロンプト
    prompt_text = f"4人家族、1週間の献立表をJSONで作成。店:{req.store}、在庫:{', '.join(req.stock)}。必ず日本語で。"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            # ログにエラー詳細を出す
            print(f"DEBUG: API Error Detail: {res_data}")
            return {
                "error": f"API Error {response.status_code}",
                "message": res_data.get("error", {}).get("message", "Request Failed")
            }

        # テキスト抽出
        text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSONを抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"raw_output": text}

    except Exception as e:
        return {"error": "Internal Error", "message": str(e)}
