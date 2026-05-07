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
    stock: list = []
    store: str = "ロピア"
    needs_lunch: list = []
    use_bento: bool = True

@app.get("/")
def read_root():
    return {"status": "ok", "api_key_loaded": bool(GEMINI_API_KEY)}

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    model_id = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    # フロントエンドの変数名（dish, score, shopping_listなど）に厳密に合わせます
    prompt_text = f"""
    4人家族の1週間の献立を作成し、以下のJSON形式で返してください。
    スーパー: {req.store}
    在庫: {', '.join(req.stock)}

    【出力JSON形式】
    {{
      "menu": [
        {{
          "day": "月曜日",
          "dish": "メイン料理名",
          "side": "副菜名",
          "nutrition_score": 90,
          "ingredients": ["材料1", "材料2"],
          "comment": "時短のコツ"
        }},
        {{
          "day": "火曜日",
          "dish": "メイン料理名",
          "side": "副菜名",
          "nutrition_score": 85,
          "ingredients": ["材料1", "材料2"],
          "comment": "栄養ポイント"
        }}
        // 日曜日まで7日分必ず作成すること
      ],
      "total_nutrition_avg": 88,
      "shopping_list": ["食材1", "食材2"]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = response.json()

        if response.status_code != 200:
            return {"error": "API Error", "detail": res_data}

        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # 不要な記号を削り、純粋なJSONのみを抽出
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "Backend Error", "message": str(e)}
