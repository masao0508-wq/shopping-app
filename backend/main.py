from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 献立候補（NG食材除外済）
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

@app.get("/menu")
def get_menu():
    days = ["月", "火", "水", "木", "金", "土", "日"]
    week = []
    veg_total = 0
    fish_count = 0

    for i in range(7):
        m = random.choice(menus)
        week.append({
            "day": days[i],
            "menu": m["name"]
        })
        veg_total += m["veg"]
        if m["type"] == "魚":
            fish_count += 1

    shopping = [
        "肉類",
        "野菜",
        "カレールー",
        "シチュールー",
        "焼きそば麺",
        "鍋スープ",
        "魚",
    ]

    return {
        "days": week,
        "shopping": shopping,
        "nutrition": {
            "veg_score": veg_total,
            "fish_count": fish_count
        }
    }
@app.post("/menu_from_stock")
def menu_from_stock(stock: list[str]):
    candidates = []

    for m in menus:
        if any(item in m["name"] for item in stock):
            candidates.append(m)

    if not candidates:
        candidates = menus

    days = ["月", "火", "水", "木", "金", "土", "日"]
    week = []

    for i in range(7):
        m = random.choice(candidates)
        week.append({
            "day": days[i],
            "menu": m["name"]
        })

    return {
        "days": week
    }
