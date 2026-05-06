from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json
import re
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
    # Pythonのf-string内で中括弧を扱うため、JSON構造を {{ }} で二重にします
    prompt = f"""
1週間の献立表を以下のJSON形式でのみ出力してください。
条件：
・4人家族分（50代夫婦、10代2人）
・買い物先：{req.store}
・在庫：{", ".join(req.stock)}
・昼食が必要な曜日ID：{req.needs_lunch}

出力フォーマット：
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
    "ingredients": [{{ "item": "材料", "amount": "分量" }}] 
  }}],
  "shopping_list": [{{ "item": "品名", "amount": "量" }}],
  "usage_tips": "使い切り案"
}}
"""
    # エラーを避けるため v1 を使用
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # 400エラーを防ぐため、問題の response_mime_type を外した標準的な構造にします
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    res = requests.post(url, json=payload)
    result = res.json()
    
    # 開発用ログ
    print(f"DEBUG: Status Code: {res.status_code}")
    print(f"DEBUG: Full Response: {result}")
    
    if "candidates" not in result:
        return {{"error": "AIからの応答にデータが含まれていません。"}}

    try:
        # 返ってきたテキストを取得
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        # AIがJSONの周りに余計な説明（```jsonなど）をつけても大丈夫なように抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except Exception as e:
        print(f"Parse Error: {str(e)}")
        return {{"error": f"データの解析に失敗しました: {str(e)}"}}
