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
    store: str = "ロピア"
    stock: List[str] = []
    must_use: str = ""
    use_bento: bool = True
    rejected_menus: List[str] = []
    volume_adjustments: Dict[str, float] = {}

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.0-flash" # 最新モデル
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    adj_text = ""
    for idx, mult in req.volume_adjustments.items():
        adj_text += f"- インデックス{idx}の日の材料を{mult}倍で算出\n"

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立をJSON形式で作成してください。
    
    【ルール】
    - 禁止食材: エビ、カニ、タコ、イカ
    - スーパー: {req.store}
    - 冷蔵庫にあるもの: {req.stock}（これらは買い物リストから除外するか、不足分のみ記載）
    - 指示: {adj_text}
    - NGリスト: {req.rejected_menus}
    
    【重要】応答は解説を一切含まず、純粋なJSONオブジェクト1つだけを出力してください。
    
    JSON構造:
    {{
      "score": 9,
      "usage_tips": "コツ",
      "menu": [
        {{ 
          "day": "月", 
          "main": {{ "name": "主菜名", "recipe": "手順" }},
          "side": {{ "name": "副菜名", "recipe": "手順" }},
          "type": "通常",
          "is_easy": true
        }}
      ],
      "stock": ["冷蔵庫の在庫"],
      "shopping_list": [ {{ "item": "食材名", "amount": 100, "unit": "g" }} ]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        
        if "candidates" not in res_data:
            return {"error": "API_ERROR", "message": "APIからの応答が空です。"}
            
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # JSON部分を抽出
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            clean_json = json.loads(json_match.group(1))
            # 必須フィールドの補完
            for field in ["menu", "shopping_list", "stock"]:
                if field not in clean_json: clean_json[field] = []
            return clean_json
        else:
            return {"error": "PARSE_ERROR", "message": "JSON形式のデータが見つかりませんでした。"}
            
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
