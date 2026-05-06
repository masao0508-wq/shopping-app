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
    # プロンプト（AIへの命令）の中だけ、JSON構造のために {{ }} を使います
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
    # APIのURLを確実に存在するパスに修正
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # Pythonとしての辞書データなので、ここは { } (一重) である必要があります
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # payload変数をそのまま渡します
        res = requests.post(url, json=payload)
        result = res.json()
        
        # エラーログ出力（デバッグ用）
        if res.status_code != 200:
            print(f"API Error: {result}")
            return {"error": f"APIエラーが発生しました(Code:{res.status_code})"}

        if "candidates" not in result:
            return {"error": "AIから有効な回答が得られませんでした。"}

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        
        # JSON部分だけを抽出
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        print(f"System Error: {str(e)}")
        return {"error": f"システムエラー: {str(e)}"}
