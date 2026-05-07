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
    
    # フロントエンドの App.js で .map() される可能性が高いキー名を網羅
    prompt_text = f"""
    あなたは優秀な献立作成アシスタントです。
    4人家族（50代夫婦、10代2人）の1週間の献立を作成し、以下のJSON構造で返してください。
    
    条件：
    - 店: {req.store}
    - 在庫: {', '.join(req.stock)}
    - 栄養スコアを各日に設定すること。

    【必須JSON構造】
    {{
      "weekly_menu": [
        {{
          "day": "月曜日",
          "menu": "メインの献立名",
          "side_dish": "副菜",
          "score": 95,
          "ingredients": ["材料1", "材料2"],
          "advice": "時短のコツ"
        }}
      ],
      "total_score": 92,
      "shopping_list": ["買うもの1", "買うもの2"]
    }}
    
    ※weekly_menuは月曜から日曜まで7日分含めてください。
    ※JSON以外のテキストは一切含めないでください。
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        # AIの生成待ちを考慮し、タイムアウトを長めに設定
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        res_data = response.json()

        if response.status_code != 200:
            return {"error": "Gemini API Error", "detail": res_data}

        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSON部分を抽出
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            # フロントエンドが 'menu' というキー名で map している場合への保険
            if "weekly_menu" in data and "menu" not in data:
                data["menu"] = data["weekly_menu"]
                
            return data
        
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "Data Processing Error", "message": str(e)}
