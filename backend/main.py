from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 OpenAI APIキー（Renderの環境変数に入れる）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# 入力モデル
# =========================
class AIRequest(BaseModel):
    stock: list[str]

# =========================
# AI献立生成
# =========================
@app.post("/ai_menu")
def ai_menu(req: AIRequest):

    prompt = f"""
    以下の食材をできるだけ使って、1週間の夕食献立を作ってください。
    食材: {", ".join(req.stock)}

    条件:
    ・7日分
    ・日本語
    ・JSON形式で出力
    ・形式：
    {{
      "days": [
        {{"day": "月", "menu": "〇〇"}},
        ...
      ],
      "shopping": ["不足食材1", "不足食材2"]
    }}
    """

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(url, headers=headers, json=payload)
    result = res.json()

    text = result["choices"][0]["message"]["content"]

    return {"result": text}
