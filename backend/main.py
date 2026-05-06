from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json
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
    store: str = "ロピア" # ロピア or 業務スーパー
    needs_lunch: list = [] # 昼食が必要な曜日 [0, 6] (月=0)

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    prompt = f"""
あなたはプロの主婦・主夫兼、栄養士です。
以下の家族構成と条件に最適な1週間の献立と買い物リストを作成してください。

【家族構成】
・父(53), 母(54), 長男(17/食べ盛り), 長女(15/食べ盛り) の計4人分。

【買い物・調理の条件】
・買い物先: {req.store}（大容量パックを使い切る工夫をして）
・調理傾向: 調味料や味付けは既製品（タレや素）を活用。
・手抜きルール: 週に2回は「超手抜き（焼きそば、冷凍食品活用、丼物など）」を組み込む。
・昼食条件: {req.needs_lunch} の曜日は昼食も追加。
・在庫状況: {", ".join(req.stock) if req.stock else "なし"}

【出力形式（厳守）】
以下のJSON形式のみで出力してください。
{{
  "score": 0-10の数値,
  "alerts": ["警告メッセージ"],
  "menu": [
    {{
      "day": "月",
      "name": "料理名",
      "is_easy": true/false,
      "lunch": "昼食名（不要ならnull）",
      "ingredients": [{{ "item": "材料名", "amount": "4人分の分量" }}]
    }}
  ],
  "shopping_list": [{{ "item": "品名", "amount": "合計数量" }}],
  "usage_tips": "大容量パックの使い回しアドバイス"
}}
"""
    # Gemini API 呼び出し
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    res = requests.post(url, json=payload)
    result = res.json()
    
    try:
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(content)
    except:
        return {"error": "AIの回答取得に失敗しました。"}

# LINE連携などは次のステップで実装（まずは献立生成を安定させます）
