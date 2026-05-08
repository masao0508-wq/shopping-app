import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
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
    needs_lunch: List[int] = []
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
    headers = {"Content-Type": "application/json"}
    
    adj_text = ""
    if req.volume_adjustments:
        for idx, mult in req.volume_adjustments.items():
            adj_text += f"- インデックス{idx}の日は材料を{mult}倍に計算\n"

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立をJSONで作成してください。
    
    【基本構成】
    - 既製品ベース（カレー、シチュー、皿うどん、鍋、麻婆豆腐の素等）: 週3日
    - ごく簡単な料理（焼くだけ、炒めるだけ等）: 週2日
    - 本格的な料理: 週2日
    - 昼ごはん（指定時）: 既製品または超簡単なもの
    
    【食材・アレルギー】
    - 禁止: エビ、カニ、タコ、イカ
    - スーパー: {req.store}（業務スーパー時は1kgポテトサラダ等の大容量惣菜を副菜に活用）
    
    【分量計算】
    - 既製品を使う場合、そのパッケージ記載の標準分量をベースに4人分を算出。
    - 指示 {adj_text} がある場合、買い物リストの数値を必ずその倍率で計算して反映すること。

    【出力ルール】
    1. usage_tips は、栄養・節約・効率のポイントを必ず「3行以内」で簡潔に。
    2. JSON構造のみを返すこと。

    {{
      "score": 9,
      "usage_tips": "1行目\\n2行目\\n3行目",
      "menu": [
        {{ 
          "day": "月", 
          "main": "主菜名", 
          "side": "副菜名（業スー惣菜含む）", 
          "type": "既製品",
          "is_easy": true, 
          "recipe_url": "https://cookpad.com/search/主菜名" 
        }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 100, "unit": "g" }} ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = response.json()
        if "candidates" not in res_data:
            return {"error": "API_ERROR", "message": res_data.get("error", {}).get("message", "Quota Exceeded")}
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        return json.loads(json_match.group(1)) if json_match else json.loads(raw_text)
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
