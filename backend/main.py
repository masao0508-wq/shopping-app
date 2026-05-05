from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 献立候補（フォールバック用）
menus = [
    {"name": "カレー"},
    {"name": "シチュー"},
    {"name": "焼きそば"},
    {"name": "鍋"},
    {"name": "豚の生姜焼き"},
    {"name": "鶏の照り焼き"},
    {"name": "サバ味噌"},
    {"name": "鮭のホイル焼き"},
]

# =========================
# 通常（ランダム）
# =========================
@app.get("/menu")
def get_menu():
    days = ["月","火","水","木","金","土","日"]
    week = [{"day": d, "menu": random.choice(menus)["name"]} for d in days]

    return {"days": week}

# =========================
# AI献立
# =========================
class AIRequest(BaseModel):
    stock: list[str] = []
    preference: str = "和食中心"

@app.post("/menu_ai")
def menu_ai(req: AIRequest):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY未設定"}

    prompt = f"""
あなたは料理のプロです。
以下の条件で1週間の献立を作成してください。

条件：
・日本語で
・月〜日
・各日1品
・現実的な料理

在庫：
{",".join(req.stock)}

好み：
{req.preference}

出力形式：
月: ○○
火: ○○
...
日: ○○
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    res = requests.post(url, json=payload)
    data = res.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        lines = text.split("\n")

        week = []
        for line in lines:
            if "：" in line:
                d, m = line.split("：")
                week.append({"day": d.strip(), "menu": m.strip()})

        return {"days": week}

    except:
        # 失敗時はランダム
        days = ["月","火","水","木","金","土","日"]
        week = [{"day": d, "menu": random.choice(menus)["name"]} for d in days]
        return {"days": week}

# =========================
# LINE通知
# =========================
@app.post("/send_line")
def send_line(data: dict):
    if not LINE_TOKEN or not USER_ID:
        return {"error": "LINE設定不足"}

    text = data.get("text", "献立")

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }

    res = requests.post(url, headers=headers, json=payload)

    return {"status": res.status_code}
