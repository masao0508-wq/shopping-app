import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    stock: list
    must_use: str
    needs_lunch: list
    # NGが出た日とその日のメニュー名を送ることで、ピンポイントで差し替え提案を可能にします
    rejected_menus: list = [] 

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    prompt_text = f"""
    献立アドバイザーとして、4人家族（50代夫婦、10代2人）の1週間分（7日分）の献立を作成してください。
    
    【厳守事項：アレルギー】
    - エビ、カニ、タコ、イカは絶対に使用禁止です。
    
    【条件】
    - スーパー: {req.store}
    - 在庫: {', '.join(req.stock)}
    - 必須食材: {req.must_use}（これを重点的に使用）
    - 却下されたメニュー: {req.rejected_menus}（これらは提案しないでください）

    【出力形式】
    JSONでのみ回答。各メニューにはクックパッド等のレシピ検索リンク（URLエンコードされた検索用リンク）を含めてください。
    {{
      "score": 9,
      "usage_tips": "アドバイス...",
      "menu": [
        {{
          "day": "月",
          "name": "料理名",
          "is_easy": true,
          "bento_tip": "...",
          "volume_tip": "...",
          "recipe_url": "https://cookpad.com/search/料理名"
        }}
      ],
      "shopping_list": [
        {{ "item": "食材名", "amount": 100, "unit": "g" }} 
      ]
    }}
    ※計算のため、amountは数値だけで返してください。
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
        res_data = response.json()
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(raw_text)
    except Exception as e:
        return {"error": str(e)}
