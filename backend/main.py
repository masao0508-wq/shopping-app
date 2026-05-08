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
    store: str = "ロピア"
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
    - 業務スーパー: 1kg惣菜、冷凍野菜、皿うどん、パウチ煮物等を活用。
    - ロピア: 自社製タレ、大容量パック肉、オリジナル惣菜を活用。

    【献立バランス】
    - 既製品ベース（週3）: 市販の素（カレー、シチュー、鍋、麻婆等）を使用。
    - 簡単料理（週2）: 既成のタレで焼くだけ・炒めるだけ。
    - 本格料理（週2）: 手作りおかず。
    
    【重要ルール】
    - レシピ(recipe)欄には、必ず使用する材料の「分量」を明記してください。
    - 既製品を使用する場合、パッケージ裏面の標準的な作り方を記載してください。
    - 主菜(main)と副菜(side)を分けて出力。
    - NG食材: エビ、カニ、タコ、イカ
    - NGメニュー: {req.rejected_menus}
    
    応答はJSONのみ。
    {{
      "menu": [
        {{ 
          "day": "月", 
          "main": {{ "name": "名", "recipe": "【材料(4人分)】...【手順】..." }},
          "side": {{ "name": "名", "recipe": "【材料(4人分)】...【手順】..." }},
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
