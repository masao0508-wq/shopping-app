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
    stock: List[str] = []
    rejected_menus: List[str] = []
    current_menu_names: Optional[List[Dict[str, str]]] = None

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 仕様書に基づき gemini-2.5-flash を指定
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    store_hints = {
        "ロピア": "みなもと牛、自社製タレ、大容量パック、PB商品、冷凍ピザ、モンスターバーガー。",
        "業務スーパー": "1kg惣菜、冷凍野菜、パウチ煮物、冷凍揚げ物、大容量調味料、皿うどんの素。"
    }

    # NGボタン（除外）対応
    ng_instruction = f"\n【絶対に含めない料理（NG）】: {', '.join(req.rejected_menus)}" if req.rejected_menus else ""

    prompt_text = f"""
    あなたは献立アプリ『Kon-Date』の専門家です。
    【店舗: {req.store}】 特徴: {store_hints.get(req.store)}
    【黄金比率】
    - 既製品ベース(3日): シチュー、皿うどん、カレー、鍋、麻婆豆腐等の素を使用。
    - 簡単料理(2日): 焼く・炒めるだけ。
    - 本格料理(2日): 手作り。
    【制約】
    1. 昼食: 「lunch」項目に必ず既製品ベース（うどん、パウチ、丼等）を含める。
    2. 禁止食材: エビ、カニ、タコ、イカ。
    3. 揚げ物: 週1回以下。
    4. レシピ: 全て「4人分」で材料・手順を詳細に。{ng_instruction}

    出力はJSON形式のみ。
    {{
      "score": 10,
      "usage_tips": "3行以内の診断コメント",
      "menu": [
        {{ "day": "月", "main": {{"name":"..","recipe":".."}}, "side": {{"name":"..","recipe":".."}}, "lunch": {{"name":"..","recipe":".."}}, "type": "既製品" }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 1, "unit": "個" }} ]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": { "response_mime_type": "application/json", "temperature": 0.8 }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        res_data = response.json()
        if "error" in res_data:
            return {"error": "API_ERROR", "message": res_data["error"]["message"]}
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_text)
    except Exception as e:
        return {"error": "SERVER_ERROR", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
