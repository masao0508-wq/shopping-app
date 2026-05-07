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

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    prompt_text = f"""
    あなたはプロの献立作成者です。4人家族向けの1週間の献立を作成してください。
    
    【重要：アレルギー禁止食材】
    エビ、カニ、タコ、イカは絶対に入れないでください。
    
    【条件】
    - スーパー: {req.store}
    - 在庫: {', '.join(req.stock)}
    - 必須使用食材: {req.must_use}
    - 避けるべきメニュー: {', '.join(req.rejected_menus)}

    【JSON形式】
    {{
      "score": 9,
      "usage_tips": "説明",
      "menu": [
        {{ "day": "月", "name": "料理名", "is_easy": true, "bento_tip": "...", "volume_tip": "...", "recipe_url": "https://cookpad.com/search/料理名" }}
      ],
      "shopping_list": [
        {{ "item": "食材名", "amount": 100, "unit": "g" }}
      ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        # --- エラーハンドリングの強化 ---
        if response.status_code != 200:
            return {"error": "API_ERROR", "message": f"Status: {response.status_code}"}

        # candidates が存在するか、中身が空でないかチェック
        candidates = res_data.get('candidates', [])
        if not candidates or 'content' not in candidates[0]:
            # 安全フィルターなどで回答が生成されなかった場合
            return {"error": "GENERATION_FAILED", "message": "AIが献立を生成できませんでした。条件を緩めてお試しください。"}

        raw_text = candidates[0]['content']['parts'][0]['text']
        
        # JSON抽出
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
