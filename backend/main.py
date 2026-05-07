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
    needs_lunch: List[int]
    use_bento: bool
    rejected_menus: List[str] = []
    # フロントから届く分量調整データ { "0": 2.0, "1": 1.5 } など
    volume_adjustments: Dict[str, float] = {}

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 接続実績のある gemini-2.5-flash と v1beta を固定
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    # 調整指示をテキスト化
    adj_text = ""
    if req.volume_adjustments:
        for idx, mult in req.volume_adjustments.items():
            adj_text += f"- インデックス{idx}のメニューは材料を{mult}倍にする\n"

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立と買い物リストをJSONで作成してください。
    
    【禁止食材】
    エビ、カニ、タコ、イカは絶対に使用しないでください。
    
    【条件】
    - スーパー: {req.store}
    - 在庫: {', '.join(req.stock)}
    - 必須食材: {req.must_use}
    - 却下済みメニュー: {', '.join(req.rejected_menus)}
    
    【分量調整指示】
    {adj_text}
    ※上記指示がある場合、買い物リスト（shopping_list）の該当食材の数値を必ず計算した上で反映させてください。

    【出力ルール】
    1. usage_tips は、栄養・節約・効率のポイントを必ず「3行以内」で簡潔にまとめてください。
    2. JSON構造のみを返し、余計な説明文は一切含めないでください。

    {{
      "score": 9,
      "usage_tips": "1行目\\n2行目\\n3行目",
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

        # エラーガード
        if "candidates" not in res_data:
            error_msg = res_data.get("error", {}).get("message", "API Error")
            return {"error": "API_ERROR", "message": error_msg}

        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # JSON抽出処理
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}
