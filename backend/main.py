import os
import json
import re
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    store: str
    stock: list
    needs_lunch: list
    use_bento: bool

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # App.jsのUI表示に必要な項目を網羅したプロンプト
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    # フロントエンドのループ処理に合わせてJSON構造を指示
    prompt_text = f"""
    あなたは献立作成のプロです。4人家族（50代夫婦、10代2人）の1週間の献立を作成してください。
    スーパー: {req.store}
    在庫食材: {', '.join(req.stock)}

    必ず以下のJSON形式のみで回答してください。
    {{
      "score": 9,
      "usage_tips": "在庫の〇〇を使い切り、節約と健康を両立しました。",
      "menu": [
        {{
          "day": "月",
          "name": "メイン料理名",
          "is_easy": true,
          "bento_tip": "夕食の残りをリメイクして入れるコツ",
          "volume_tip": "10代向けにボリュームを出す工夫"
        }},
        {{
          "day": "火",
          "name": "メイン料理名",
          "is_easy": false,
          "bento_tip": "冷めても美味しいおかずの詰め方",
          "volume_tip": "食べ盛りも満足する副菜の提案"
        }}
        // 日曜日まで7日間分必ず作成
      ],
      "shopping_list": [
        {{ "item": "食材名", "amount": "数量（例: 200g, 1袋）" }}
      ]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        if response.status_code != 200:
            return {"error": "API Error", "message": res_data.get("error", {}).get("message")}

        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSON部分を正確に抽出
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            # App.js の needs_lunch 状態に基づき lunch キーを付与
            days_labels = ["月", "火", "水", "木", "金", "土", "日"]
            for i, menu_item in enumerate(data.get("menu", [])):
                if i in req.needs_lunch:
                    menu_item["lunch"] = "手軽に作れるボリュームランチ"
                else:
                    menu_item["lunch"] = None
            
            return data
            
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "Internal Error", "message": str(e)}
