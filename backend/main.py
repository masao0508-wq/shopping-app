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
    # ご指摘の通り、使用可能な最新モデル gemini-2.5-flash を指定
    # 安定性を考慮し、最新の v1 エンドポイントを使用
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    # 400エラーを防ぐため、リクエスト構造を最新のAPI仕様に準拠
    prompt = f"4人家族（50代夫婦、10代2人）の1週間の献立表をJSON形式で作成してください。店:{req.store}、在庫:{', '.join(req.stock)}。必ず日本語で出力してください。"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        # 失敗時の原因特定のため、詳細をレスポンスに含める
        if response.status_code != 200:
            return {
                "error": f"API Error {response.status_code}",
                "message": res_data.get("error", {}).get("message", "Unknown error"),
                "model_used": model_id
            }

        # レスポンスからテキスト部分を抽出
        text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSONを抽出してパース
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        return {"error": "Internal Server Error", "detail": str(e)}
