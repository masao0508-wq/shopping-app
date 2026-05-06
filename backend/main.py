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
    # プロンプト内のJSON構造は {{ }} (二重) にする必要があります
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
    # URLを最も汎用的な 'v1beta' かつモデル名を修正
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    payload = {{
        "contents": [{{
            "parts": [{{ "text": prompt }}]
        }}]
    }}
    
    # 実際のリクエスト実行（エラーハンドリングを強化）
    try:
        # Pythonコードとしての辞書なので、ここは { } (一重) です
        res = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        })
        result = res.json()
        
        if "candidates" not in result:
            print(f"Gemini Error: {result}")
            return {"error": "AIが回答を拒絶しました。APIキーまたはモデル設定を確認してください。"}

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        print(f"System Error: {str(e)}")
        return {"error": f"システムエラーが発生しました: {str(e)}"}
