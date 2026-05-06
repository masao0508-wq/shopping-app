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
    store: str = "ロピア"
    needs_lunch: list = [] # [0, 6] (月=0)
    use_bento: bool = True # 弁当スライド機能

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    prompt = f"""
あなたはプロの主夫兼、栄養士です。家族4人分の1週間の献立を作成してください。

【家族構成とニーズ】
・父(53), 母(54): 重すぎない健康的なバランス。
・長男(17), 長女(15): 代謝が良く食べ盛り。メインはガッツリ多めに。
・買い物先: {req.store}（大容量パックを効率的に使い切る）。
・調理スタイル: 既製品のタレ・素を賢く使い、時短する。

【特別ルール】
1. 弁当スライド: {req.use_bento} がTrueなら、夕食を多めに作り、翌日のお弁当（お子様2人分）に回せるメニューを優先。
2. ガッツリ度調整: 同じ主菜でも「子供は揚げ物、親は焼き物」や、子供だけ1品追加するなどの配慮を提案に含める。
3. 手抜き: 週2回は超手抜き（焼きそば、丼、冷食活用）。
4. 昼食: {req.needs_lunch} の曜日は昼食も追加。
5. 在庫: {", ".join(req.stock) if req.stock else "なし"}

【出力形式（JSONのみ）】
{{
  "score": 0-10,
  "alerts": ["栄養や在庫に関する警告"],
  "menu": [
    {{
      "day": "月",
      "name": "夕食のメイン料理名",
      "is_easy": true/false,
      "lunch": "昼食名（不要ならnull）",
      "bento_tip": "翌日の弁当への活用法",
      "volume_tip": "10代向けのボリュームアップ案",
      "ingredients": [{{ "item": "材料名", "amount": "4人分の分量" }}]
    }}
  ],
  "shopping_list": [{{ "item": "品名", "amount": "合計数量" }}],
  "usage_tips": "ロピア/業スーの大容量食材の使い切り計画"
}}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    res = requests.post(url, json=payload)
    try:
        content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(content)
    except:
        return {"error": "AIの回答取得に失敗しました。"}
