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
    # JSONの雛形部分を {{ }} に変更しています
    prompt = f"""
1週間の献立表をJSONで作ってください。
条件：
・4人家族分（50代夫婦、10代2人）
・買い物先：{req.store}
・在庫：{", ".join(req.stock)}
・昼食が必要な曜日：{req.needs_lunch}

出力は以下のJSON形式のみ：
{{
  "score": 8,
  "alerts": [],
  "menu": [{{ 
    "day": "月", 
    "name": "料理名", 
    "is_easy": false, 
    "lunch": null, 
    "bento_tip": "案", 
    "volume_tip": "案", 
    "ingredients": [{{ "item": "肉", "amount": "500g" }}] 
  }}],
  "shopping_list": [{{ "item": "肉", "amount": "1kg" }}],
  "usage_tips": "使い切り案"
}}
"""
    # 前回の修正通り v1 を指定
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    # ...以下略
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
