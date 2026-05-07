import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
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
    store: str
    stock: List[str]
    must_use: str
    needs_lunch: List[int]
    use_bento: bool
    rejected_menus: List[str] = []

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 接続に成功していた gemini-2.5-flash と v1beta を維持
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立を作成してください。
    【禁止】エビ、カニ、タコ、イカ
    【条件】店:{req.store}, 在庫:{','.join(req.stock)}, 必須:{req.must_use}, 却下:{','.join(req.rejected_menus)}

    必ず以下のJSON構造のみで回答してください。
    {{
      "score": 9,
      "usage_tips": "コツ",
      "menu": [
        {{ "day": "月", "name": "料理名", "is_easy": true, "bento_tip": "...", "volume_tip": "...", "recipe_url": "https://cookpad.com/search/料理名" }}
      ],
      "shopping_list": [
        {{ "item": "食材", "amount": 100, "unit": "g" }}
      ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        # --- candidatesエラーの徹底ガード ---
        if "candidates" not in res_data:
            # エラー内容をフロントに投げて、'candidates'で落ちるのを防ぐ
            error_msg = res_data.get("error", {}).get("message", "Unknown API Error")
            return {"error": "API_ERROR", "message": error_msg}

        # 中身を取り出す前に存在チェック
        candidate = res_data["candidates"][0]
        if "content" not in candidate or "parts" not in candidate["content"]:
            return {"error": "EMPTY_RESPONSE", "message": "AIの回答が空でした。もう一度お試しください。"}

        raw_text = candidate["content"]["parts"][0]["text"]
        
        # JSONを抜き出す
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return json.loads(raw_text)

    except Exception as e:
        # ここで例外をキャッチして、フロントエンドのmapエラーを未然に防ぐ
        return {"error": "PYTHON_ERROR", "message": str(e)}
