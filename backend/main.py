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
    return {"status": "ok", "message": "Backend is running"}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # CODEX推奨：v1beta と最新モデル gemini-2.0-flash を使用
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    # CODEX推奨：APIキーをヘッダー（x-goog-api-key）で渡す
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    # プロンプト（文字化け対策のため、シンプルな記述を心がけています）
    prompt = f"Create a 7-day meal plan in JSON. Family of 4, Store: {req.store}, Stock: {', '.join(req.stock)}. Use Japanese for food names."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            return {"error": f"API Error {response.status_code}", "detail": res_data}

        # Gemini 2.0系のレスポンス構造からテキストを抽出
        text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSON部分を抽出して返却
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        return {"error": str(e)}
