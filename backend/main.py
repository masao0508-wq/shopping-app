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

# CORS設定をさらに広めに設定
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
    
    adj_text = ""
    for idx, mult in req.volume_adjustments.items():
        adj_text += f"- インデックス{idx}の日の材料を{mult}倍で算出\n"

# backend/main.py の prompt_text を以下のように微調整してください
    prompt_text = f"""
    あなたはプロの献立アドバイザーです。

    【最優先指示】
    1. 指示 {adj_text} がある場合、現在の献立名は絶対に変えず、「shopping_list」の分量(amount)のみを倍率通りに増やしてください。
    2. 冷蔵庫にあるもの {req.stock} は買い物リストから除外するか、不足分のみをリストアップしてください。
    3. 出力には必ず "stock"（冷蔵庫の在庫リスト）をそのまま含めてください。
    
    【ルール】
    - 禁止食材: エビ、カニ、タコ、イカ
    - 各料理に "recipe" を含める。
    
    JSON構造:
    {{
      "score": 9,
      "usage_tips": "コツ",
      "menu": [...],
      "stock": ["肉", "玉ねぎ"],
      "shopping_list": [ {{ "item": "食材", "amount": 100, "unit": "g" }} ]
    }}
    """
    
    # 修正ポイント：二重中括弧を避け、辞書として定義してから渡す
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ]
    }
    
    try:
        # json=payload として渡すことで requests が自動で適切な JSON に変換します
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        
        if "candidates" not in res_data:
            return {"error": "API_ERROR", "message": "APIからの応答が不正です。"}
            
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # JSON部分を抽出
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            return json.loads(raw_text)
            
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
