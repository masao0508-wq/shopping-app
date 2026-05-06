from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json
import re  # 正規表現を追加
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
    stock: list = []
    store: str = "ロピア"
    needs_lunch: list = []
    use_bento: bool = True

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    prompt = f"""
あなたはプロの主婦。家族4人分（父53歳、母54歳、長男17歳、長女15歳）の献立を作成してください。
条件：買い物先は「{req.store}」。在庫「{", ".join(req.stock)}」を活用。
週2回は手抜き料理。翌日の弁当スライドを考慮。10代向けボリューム案を付与。
昼食が必要な曜日ID: {req.needs_lunch} (0=月)

以下のJSON形式のみで出力してください。
{{
  "score": 0-10,
  "alerts": [],
  "menu": [{{ "day": "月", "name": "料理名", "is_easy": true, "lunch": "昼食名", "bento_tip": "弁当案", "volume_tip": "10代案", "ingredients": [{{ "item": "肉", "amount": "500g" }}] }}],
  "shopping_list": [{{ "item": "肉", "amount": "1kg" }}],
  "usage_tips": "使い切りアドバイス"
}}
# モデル名を gemini-pro に戻すか、バージョン指定を v1 に変更します
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    res = requests.post(url, json=payload)
    result = res.json()
    
    try:
        # AIの返答からJSONだけを取り出す
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        # JSON以外の文字が混ざっていた場合の掃除
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except Exception as e:
        print(f"AI Response Error: {result}")
        return {"error": f"AIの回答を解析できませんでした。内容: {str(e)}"}
