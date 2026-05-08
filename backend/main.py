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
    store: str = "ロピア" # ロピア or 業務スーパー
    stock: List[str] = []
    rejected_menus: List[str] = []
    volume_adjustments: Dict[str, float] = {}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立をJSONで作成してください。
    
    【買い物先: {req.store}】
    - {req.store}で安く手に入る食材や既製品をベースにしてください。
    - 業務スーパーの場合: 1kgポテトサラダ、冷凍野菜、パウチのカレーや煮物、皿うどんの素等を活用。
    - ロピアの場合: 自社製焼肉のタレ、丸ごと煮豚、オリジナル惣菜、大容量パック肉を活用。

    【献立構成（週7日）】
    1. 既製品ベース（週3）: カレー、シチュー、皿うどん、鍋の素、麻婆豆腐の素、パスタソース等。
    2. 簡単料理（週2）: 味付け肉を焼くだけ、カット野菜と肉の炒めもの等（味付けは既製のタレ）。
    3. 本格料理（週2）: 煮込み料理や手作りおかず。
    
    【ルール】
    - 分量は既製品（パッケージ）の標準的な4人前表記に従う。
    - 主菜(main)と副菜(side)は完全に分けて記載。
    - 業務スーパー選択時は、副菜に1kg惣菜シリーズを積極的に採用。
    - 冷蔵庫にあるもの: {req.stock}
    - NGリスト: {req.rejected_menus}
    
    応答はJSONのみ。
    {{
      "menu": [
        {{ 
          "day": "月", 
          "main": {{ "name": "主菜名(既製品名等)", "recipe": "パッケージ通りに作る手順" }},
          "side": {{ "name": "副菜名", "recipe": "盛り付けや簡単な手順" }},
          "type": "既製品/簡単/本格"
        }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 1, "unit": "個/g" }} ],
      "stock": {req.stock}
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": { "response_mime_type": "application/json" }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(re.search(r'({.*})', raw_text, re.DOTALL).group(1))
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
