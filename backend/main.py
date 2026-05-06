from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import re
from dotenv import load_dotenv
# 1. Google公式のSDKをインポート
from google import genai

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

# 2. 公式クライアントを初期化（自動的に環境変数 GEMINI_API_KEY を読み込みます）
client = genai.Client()

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

    try:
        # モデル名を 'gemini-1.5-flash' から 'gemini-pro' に変更
        response = client.models.generate_content(
            model='gemini-pro', 
            contents=prompt,
        )
        
        text = response.text
        
        # JSON部分を抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        print(f"--- System Error ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        return {"error": f"エラーが発生しました: {str(e)}"}
