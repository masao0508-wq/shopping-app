from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import re
from dotenv import load_dotenv
# Google公式SDK
from google import genai

load_dotenv()
app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 【重要】api_version="v1" を指定して、不安定な v1beta を回避します
# これにより、リンク先の記事と同様に「安定版」の窓口を使用します
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    api_version="v1"
)

class MenuRequest(BaseModel):
    stock: list = []
    store: str = "ロピア"
    needs_lunch: list = []
    use_bento: bool = True

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # AIへのプロンプト
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
        # モデル名は安定版で確実に存在する 'gemini-1.5-flash' を使用
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        
        text = response.text
        
        # JSON部分を抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        # ログに詳細なエラーを表示
        print(f"--- Gemini API Error Details ---")
        print(f"Error: {str(e)}")
        return {"error": f"API実行エラー: {str(e)}"}
