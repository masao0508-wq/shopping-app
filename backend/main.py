from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import re
from dotenv import load_dotenv
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

# クライアントの初期化を関数外で行う際のエラーを避けるため、
# APIキーを明示的に取得します。
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# APIキーが取得できない場合にプロセスが落ちないようチェック
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set in environment variables.")

# 安定版の v1 を指定
client = genai.Client(
    api_key=GEMINI_API_KEY,
    api_version="v1"
)

class MenuRequest(BaseModel):
    stock: list = []
    store: str = "ロピア"
    needs_lunch: list = []
    use_bento: bool = True

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running"}

@app.post("/generate_menu")
async def generate_menu(req: MenuRequest):
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
        # モデル呼び出し
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        
        text = response.text
        
        # JSON抽出のロジック
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {"error": str(e)}
