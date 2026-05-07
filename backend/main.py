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
    
    # 指示を具体的にし、栄養スコアや買い物リストの計算をAIに命じます
    prompt_text = f"""
    あなたはプロの献立アドバイザーです。4人家族（50代夫婦、10代2人）向けに
    {req.store}で買える食材を活かした1週間の献立を作成してください。
    
    【条件】
    - 在庫食材を優先して使うこと: {', '.join(req.stock)}
    - お弁当が必要な場合、夕食の残りを活用する工夫を含める。
    - 栄養バランス（PFCバランス、ビタミン、塩分）を考慮する。
    
    必ず以下のJSON形式でのみ回答してください。
    {{
      "menu": [
        {{ 
          "day": "月曜日", 
          "dish": "メイン料理名", 
          "side": "副菜名",
          "nutrition_score": 95, 
          "ingredients": ["材料1", "材料2"],
          "comment": "奥様への一言アドバイス（時短ポイントなど）"
        }}
        // これを日曜日まで繰り返す
      ],
      "total_nutrition_avg": 90,
      "shopping_list": ["食材名(数量)", "食材名(数量)"]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        res_data = response.json()

        if response.status_code != 200:
            return {"error": f"API Error {response.status_code}", "message": res_data.get("error", {}).get("message")}

        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # AIがJSON以外の文字を混ぜても抽出できるようにする
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            parsed_data = json.loads(match.group())
            # フロントエンドの期待する構造に微調整（必要に応じて）
            return parsed_data
        
        return json.loads(raw_text)

    except Exception as e:
        return {"error": "Processing Error", "message": str(e)}
