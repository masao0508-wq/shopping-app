import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
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
    use_bento: bool
    rejected_menus: List[str] = []
    volume_adjustments: Dict[str, float] = {}

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    # 分量調整のテキスト生成
    adj_text = ""
    for idx, mult in req.volume_adjustments.items():
        adj_text += f"- インデックス{idx}の日の材料を{mult}倍で算出\n"

    # プロンプト（必ず関数内で定義）
    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立JSONを作成してください。

    【基本構成】
    - 既製品ベース（カレー、シチュー、鍋等の素）: 週3日
    - ごく簡単な料理（焼くだけ、炒めるだけ等）: 週2日
    - 本格的な料理: 週2日

    【ルール】
    - 禁止: エビ、カニ、タコ、イカ
    - スーパー: {req.store}
    - 外部リンクは禁止。レシピ（材料と手順）を各料理に含めること。
    - 指示 {adj_text} がある場合、買い物リストの数値を必ずその倍率で計算すること。
    - NGリスト {req.rejected_menus} の料理は避け、栄養バランスを維持した代替案を出すこと。

    JSON構造:
    {{
      "score": 9,
      "usage_tips": "3行以内のコツ",
      "menu": [
        {{ 
          "day": "月", 
          "main": {{ "name": "主菜名", "recipe": "手順" }},
          "side": {{ "name": "副菜名", "recipe": "手順" }},
          "type": "既製品",
          "is_easy": true
        }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 100, "unit": "g" }} ]
    }}
    """
    
    payload = {{"contents": [{{"parts": [{{"text": prompt_text}}]}}]}}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        
        if "candidates" not in res_data:
            return {{"error": "API_ERROR", "message": "Quota exceeded or API error"}}
            
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        json_match = re.search(r'({{.*}})', raw_text, re.DOTALL)
        return json.loads(json_match.group(1)) if json_match else json.loads(raw_text)
        
    except Exception as e:
        return {{"error": "SERVER_ERROR", "message": str(e)}}
