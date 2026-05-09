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
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    store_info = ""
    if req.store == "ロピア":
        store_info = "ロピアの強み：『みなもと牛』『自社製みなもと豚』などの大容量肉、自社製タレ、モンスターバーガー等のデカ盛り惣菜、冷凍ピザ。"
    else:
        store_info = "業務スーパーの強み：1kg入りのポテトサラダ等のパウチ惣菜、揚げるだけの冷凍フライ、大容量の冷凍野菜、直輸入のパスタ・ソース、皿うどんの素。"

    prompt_text = f"""
    あなたは献立アプリ『Kon-Date』の専門アドバイザーです。4人家族向けの1週間の献立を以下の条件で作成してください。
    
    【店舗情報: {req.store}】
    {store_info}
    - 上記の店舗で実際に販売されている代表的な製品を積極的に献立に組み込んでください。

    【献立ルール】
    - 揚げ物は週1回（1割以下）に厳選。
    - 構成: 既製品ベース(3日)、簡単料理(2日)、本格料理(2日)。
    - 味付け: 市販の「鍋の素」「カレールー」等の活用を前提。
    - 禁止食材: エビ、カニ、タコ、イカ。
    - NG済み: {req.rejected_menus}

    応答は以下のJSON形式のみ。
    - "usage_tips"（栄養バランススコアのコメント）は「3行以内」で簡潔に。
    
    {{
      "score": 10,
      "usage_tips": "コメント（3行以内）",
      "menu": [
        {{ "day": "月", "main": {{"name":"料理名","recipe":"..."}}, "side": {{"name":"料理名","recipe":"..."}}, "type": "既製品" }}
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
