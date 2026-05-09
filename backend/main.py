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
    model_id = "gemini-2.0-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    store_hints = {
        "ロピア": "みなもと牛/豚、自社製タレ、モンスターバーガー惣菜、冷凍ピザ、PBパスタソース。",
        "業務スーパー": "1kg惣菜、冷凍野菜、皿うどんの素、麻婆豆腐の素、パウチ煮物、冷凍揚げ物。"
    }

    calc_instruction = ""
    if req.current_menu_names:
        menu_summary = "\n".join([f"{m['day']}: {m['main']} / {m['side']}" for m in req.current_menu_names])
        calc_instruction = f"\n重要：以下のメニューの「4人分」の材料のみを正確に買い物リストに計上してください：\n{menu_summary}"

    prompt_text = f"""
    あなたは献立アプリ『Kon-Date』のアドバイザーです。4人家族向けの1週間献立を生成してください。
    
    【店舗: {req.store}】活用製品: {store_hints.get(req.store)}
    
    【ルール】
    1. 構成: 既製品ベース(3日)、簡単料理(2日)、本格料理(2日)。味付けは既製の素を優先。
    2. 昼ごはん: 既製品や超簡単なもの(うどん、パウチ等)を「lunch」項目に提案。
    3. 揚げ物: 週1回(1割以下)に制限。
    4. 禁止: エビ、カニ、タコ、イカ。
    5. レシピ: 包装記載の分量をベースに、4人分で材料・手順を詳細に。
    6. NGリスト: {req.rejected_menus}
    {calc_instruction}

    【出力形式】JSONのみ。usage_tipsは3行以内で。
    {{
      "score": 10,
      "usage_tips": "栄養バランス等のコメント(3行以内)",
      "menu": [
        {{ 
          "day": "月", 
          "main": {{"name":"料理名","recipe":"材料・手順"}}, 
          "side": {{"name":"料理名","recipe":"材料・手順"}},
          "lunch": {{"name":"料理名","recipe":"材料・手順"}},
          "type": "既製品" 
        }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 1, "unit": "個" }} ]
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
