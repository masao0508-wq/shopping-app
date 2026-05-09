import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
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
    rejected_menus: List[str] = []

@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    # 仕様: gemini-2.5-flash 固定
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
    
    prompt_text = f"""
    献立アプリ『Kon-Date』用。店舗: {req.store}
    黄金比率: 既製品ベース(3日)、簡単(2日)、本格(2日)。
    制約: エビ・カニ・タコ・イカ禁止。揚げ物週1以下。4人分。
    昼食(lunch)必須。NG料理: {req.rejected_menus}
    
    JSON形式で出力。材料は必ず「- 材料名: 数値 単位」の形式でレシピ(recipe)に含めること。
    {{
      "usage_tips": "AI診断",
      "menu": [
        {{ "day": "月", "main": {{"name":"..","recipe":".."}}, "side": {{"name":"..","recipe":".."}}, "lunch": {{"name":"..","recipe":".."}}, "type": "既製品" }}
      ],
      "shopping_list": [ {{ "item": "..", "amount": 1.0, "unit": ".." }} ]
    }}
    """
    
    try:
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": { "response_mime_type": "application/json", "temperature": 0.7 }
        }, timeout=60)
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
