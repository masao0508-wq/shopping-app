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

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 最新の Gemini 2.0 Flash を使用
    model_id = "gemini-2.0-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    adj_text = ""
    for idx, mult in req.volume_adjustments.items():
        adj_text += f"- インデックス{idx}の日の材料を{mult}倍で算出\n"

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立をJSON形式で作成してください。
    
    【ルール】
    - 禁止食材: エビ、カニ、タコ、イカ
    - スーパー: {req.store}
    - 指示: {adj_text}
    
    応答は解説を一切含まず、純粋なJSONオブジェクト1つだけを出力してください。
    
    JSON構造:
    {{
      "score": 9,
      "usage_tips": "コツ",
      "menu": [
        {{ 
          "day": "月", 
          "main": {{ "name": "主菜名", "recipe": "手順" }},
          "side": {{ "name": "副菜名", "recipe": "手順" }},
          "type": "通常"
        }}
      ],
      "stock": {req.stock},
      "shopping_list": [ {{ "item": "食材名", "amount": 100, "unit": "g" }} ]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        # 安全フィルターをオフに近づけて回答拒否（空の応答）を防ぐ
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "response_mime_type": "application/json" # JSONモードを強制
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        
        if "error" in res_data:
            return {"error": "GOOGLE_API_ERROR", "message": res_data["error"].get("message")}

        if "candidates" not in res_data or not res_data["candidates"]:
            return {"error": "API_EMPTY", "message": "AIが回答を生成できませんでした。安全設定を確認してください。"}
            
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # JSONの抽出ロジック
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            return {"error": "PARSE_ERROR", "message": "JSON形式が見つかりません。"}
            
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
