from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import requests
import os
from dotenv import load_dotenv

# .env読み込み（ローカル用）
load_dotenv()

app = FastAPI()

# =========================
# CORS設定
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 環境変数
# =========================
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")

# 安全チェック
if not LINE_TOKEN:
    print("⚠ LINE_TOKEN 未設定")
if not USER_ID:
    print("⚠ USER_ID 未設定")

# =========================
# 献立候補
# =========================
menus = [
    {"name": "カレー", "type": "肉", "veg": 1},
    {"name": "シチュー", "type": "肉", "veg": 2},
    {"name": "焼きそば", "type": "肉", "veg": 1},
    {"name": "鍋", "type": "肉", "veg": 3},
    {"name": "豚の生姜焼き", "type": "肉", "veg": 1},
    {"name": "鶏の照り焼き", "type": "肉", "veg": 1},
    {"name": "サバ味噌", "type": "魚", "veg": 1},
    {"name": "鮭のホイル焼き", "type": "魚", "veg": 1},
]

# =========================
# 通常献立
# =========================
@app.get("/menu")
def get_menu():
    days = ["月", "火", "水", "木", "金", "土", "日"]
    week = []
    veg_total = 0
    fish_count = 0

    for i in range(7):
        m = random.choice(menus)
        week.append({"day": days[i], "menu": m["name"]})
        veg_total += m["veg"]
        if m["type"] == "魚":
            fish_count += 1

    shopping = ["肉", "野菜", "魚", "調味料"]

    return {
        "days": week,
        "shopping": shopping,
        "nutrition": {
            "veg_score": veg_total,
            "fish_count": fish_count
        }
    }

# =========================
# 在庫入力モデル
# =========================
class StockRequest(BaseModel):
    stock: list[str]

# =========================
# 在庫から献立生成
# =========================
@app.post("/menu_from_stock")
def menu_from_stock(req: StockRequest):
    days = ["月", "火", "水", "木", "金", "土", "日"]

    week = []
    for i in range(7):
        m = random.choice(menus)
        week.append({"day": days[i], "menu": m["name"]})

    # 必要食材
    required = ["肉", "野菜", "魚"]

    # 不足食材
    missing = [r for r in required if r not in req.stock]

    return {
        "days": week,
        "missing": missing
    }

# =========================
# LINE通知
# =========================
@app.post("/send_line")
def send_line(data: dict):
    if not LINE_TOKEN or not USER_ID:
        return {"error": "LINE設定が不足しています"}

    text = data.get("text", "献立情報")

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": USER_ID,
        "messages": [
            {"type": "text", "text": text}
        ]
    }

    res = requests.post(url, headers=headers, json=payload)

    return {
        "status": res.status_code,
        "response": res.text
    }
