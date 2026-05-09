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
    rejected_menus: List[str] = []
    current_menu_names: Optional[List[Dict[str, str]]] = None

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    # 買い物リストの引き算・足し算を正確にするための特定指示
    calc_instruction = ""
    if req.current_menu_names:
        menu_list = "\n".join([f"{m['day']}: 主菜 {m['main']}, 副菜 {m['side']}" for m in req.current_menu_names])
        calc_instruction = f"重要：以下の確定済み献立リストのみに必要な材料を計算し、買い物リストを作成してください（これ以外の料理の材料は含めないでください）：\n{menu_list}"

    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族向けの1週間の献立をJSON形式で作成してください。
    
    【買い物先: {req.store}】
    - ロピア: 自社製タレ、大容量肉、オリジナル惣菜(煮豚等)を活用。
    - 業務スーパー: 1kg惣菜、冷凍野菜、パウチ煮物、皿うどん等を活用。

    【献立ルール】
    - 揚げ物は「1割以下」に制限（週に1回未満）。
    - 構成: 既製品ベース(週3)、簡単料理(週2)、本格料理(週2)。
    - 味付け: 既製品の素（カレー、シチュー、鍋、麻婆等）の使用を前提とする。
    - 禁止食材: エビ、カニ、タコ、イカ。
    - レシピ: 4人分の具体的な「材料・分量」と「手順」をパッケージ記載通りに詳しく。
    - NGメニュー（これらは避ける）: {req.rejected_menus}
    {calc_instruction}

    応答はJSONのみ。
    {{
      "score": 10,
      "usage_tips": "今回の献立のポイントと節約のコツ",
      "menu": [
        {{ 
          "day": "月", 
          "main": {{"name":"料理名","recipe":"【材料(4人分)】...【手順】..."}}, 
          "side": {{"name":"料理名","recipe":"【材料(4人分)】...【手順】..."}}, 
          "type": "既製品" 
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
