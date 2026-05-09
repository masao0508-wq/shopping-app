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
    # 【最優先】ユーザー様の環境で最も安定していたIDに固定
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    store_hints = {
        "ロピア": "みなもと牛、自社製タレ、大容量パック、PBパスタソース、冷凍ピザ、モンスターバーガー。",
        "業務スーパー": "1kg惣菜、冷凍野菜、パウチ煮物、冷凍揚げ物、大容量調味料、皿うどんの素。"
    }

    calc_instruction = ""
    if req.current_menu_names:
        menu_summary = "\n".join([f"{m['day']}: {m['main']} / {m['side']}" for m in req.current_menu_names])
        calc_instruction = f"\n重要：以下のメニューに基づき、「4人分」の正確な買い物リストのみを計算して出力してください：\n{menu_summary}"

    prompt_text = f"""
    あなたは献立アプリ『Kon-Date』の専門家です。
    【店舗: {req.store}】 特徴: {store_hints.get(req.store)}
    【制約】
    1. 構成: 既製品ベース(3日)、簡単料理(2日)、本格(2日)。
    2. 昼食: 「lunch」項目に必ず既製品メニュー（うどん、丼、パウチ等）を含める。
    3. 禁止食材: エビ、カニ、タコ、イカ。
    4. 揚げ物: 週1回以下。
    5. レシピ: 全て「4人分」で材料と手順を詳細に。
    6. NGリスト: {req.rejected_menus}
    {calc_instruction}

    出力は必ず以下のJSON形式のみで、解説は一切不要です。
    {{
      "score": 10,
      "usage_tips": "診断コメント(3行以内)",
      "menu": [
        {{ "day": "月", "main": {{"name":"..","recipe":".."}}, "side": {{"name":"..","recipe":".."}}, "lunch": {{"name":"..","recipe":".."}}, "type": ".." }}
      ],
      "shopping_list": [ {{ "item": "食材名", "amount": 1, "unit": "個" }} ]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": { 
            "response_mime_type": "application/json", 
            "temperature": 0.8 
        }
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
