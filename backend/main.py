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

# CORS設定：Vercelからの通信を許可
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
    # AIへの指示（プロンプト）
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

    # 修正前：url = f"https://generativelanguage.googleapis.com/v1/models/..."
# 修正後（これにしてください）：
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}

    try:
        # APIにリクエストを送信
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # 404が出た場合に備えて詳細をログ出力
        if response.status_code != 200:
            print(f"--- Gemini API Error Detail ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            return {"error": f"APIエラー(Code:{response.status_code})。詳細はRenderのログを確認してください。"}

        result = response.json()
        
        # AIの回答テキストを取得
        if "candidates" in result and len(result["candidates"]) > 0:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # JSON部分を抽出（マークダウンの ```json ... ``` を除去）
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        else:
            return {"error": "AIからの応答が空でした。"}

    except Exception as e:
        print(f"--- System Error ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        return {"error": "システムエラーが発生しました。"}
