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
    must_use: str  # 必須食材
    needs_lunch: list
    use_bento: bool

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    # プロンプトにアレルギー情報と必須食材の指示を追加
    prompt_text = f"""
    あなたは献立作成のプロです。4人家族（50代夫婦、10代2人）向けに献立を作成してください。
    
    【重要：制限事項】
    - アレルギーのため「エビ、カニ、タコ、イカ」は絶対に含めないでください。
    
    【条件】
    - スーパー: {req.store}
    - 在庫食材: {', '.join(req.stock)}
    - 優先・必須食材: {req.must_use} (この食材を積極的に複数のメニューに組み込んでください)

    JSON形式でのみ回答してください。
    {{
      "score": 9,
      "usage_tips": "必須食材を活かしたバリエーション豊かなメニューです。",
      "menu": [
        {{
          "day": "月",
          "name": "料理名",
          "is_easy": true,
          "bento_tip": "詰め方のコツ",
          "volume_tip": "ボリュームアップのコツ"
        }}
      ],
      "shopping_list": [
        {{ "item": "食材名", "amount": "数量" }}
      ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
        res_data = response.json()
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            # 昼食フラグの初期化
            for i, m in enumerate(data.get("menu", [])):
                m["lunch"] = "昨日の残り" if i in req.needs_lunch else None
            return data
        return json.loads(raw_text)
    except Exception as e:
        return {"error": str(e)}
