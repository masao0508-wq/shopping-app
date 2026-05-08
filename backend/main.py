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

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立JSONを作成してください。
    
    【ルール】
    - 禁止食材: エビ、カニ、タコ、イカ
    - スーパー: {req.store}
    - 各料理に "recipe"（手順）を必ず含める。
    - 指示 {adj_text} があれば分量をその倍率で計算。
    - NGリスト {req.rejected_menus} は避ける。

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
