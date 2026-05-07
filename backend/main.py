import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

app = FastAPI()

# CORS設定: フロントエンド（Vercel等）からのアクセスを許可
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
    # 最新の2.5-flash-liteを使用
    model_id = "gemini-2.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # フロントエンドが data.menu.map() でエラーを出さないよう構造を強制
    prompt_text = f"""
    4人家族（50代夫婦、10代2人）の1週間の献立表を日本語で作成してください。
    スーパー: {req.store}
    現在の在庫: {', '.join(req.stock)}

    必ず以下のJSON形式のみで回答してください。余計な説明文は一切不要です。
    {{
      "menu": [
        {{ "day": "月曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "火曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "水曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "木曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "金曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "土曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }},
        {{ "day": "日曜日", "dish": "料理名", "ingredients": ["材料1", "材料2"] }}
      ],
      "shopping_list": ["買うべきもの1", "買うべきもの2"]
    }}
    """
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            print(f"DEBUG API Error: {res_data}")
            return {
                "error": f"API Error {response.status_code}",
                "message": res_data.get("error", {}).get("message", "Request Failed")
            }

        # Geminiからのテキスト回答を抽出
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # 文字列からJSONオブジェクトに変換
        # re.DOTALLを使って、改行を含むJSON全体を抽出
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        
        # 万が一正規表現で失敗した場合の予備
        return json.loads(raw_text)

    except Exception as e:
        print(f"Internal Error: {str(e)}")
        return {"error": "Internal Server Error", "message": str(e)}
