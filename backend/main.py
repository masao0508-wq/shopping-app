from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

# CORS設定（Reactから叩くため）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# データ定義
# -----------------------------
menus = [
    {"name": "カレー", "ingredients": ["肉", "じゃがいも", "にんじん", "玉ねぎ"], "veg": 2, "type": "肉"},
    {"name": "シチュー", "ingredients": ["肉", "じゃがいも", "にんじん", "玉ねぎ"], "veg": 2, "type": "肉"},
    {"name": "焼きそば", "ingredients": ["豚肉", "キャベツ", "麺"], "veg": 1, "type": "肉"},
    {"name": "鍋", "ingredients": ["肉", "白菜", "豆腐"], "veg": 3, "type": "肉"},
    {"name": "豚の生姜焼き", "ingredients": ["豚肉", "玉ねぎ"], "veg": 1, "type": "肉"},
    {"name": "鶏の照り焼き", "ingredients": ["鶏肉"], "veg": 0, "type": "肉"},
    {"name": "サバ味噌", "ingredients": ["サバ", "味噌"], "veg": 0, "type": "魚"},
    {"name": "鮭のホイル焼き", "ingredients": ["鮭", "きのこ"], "veg": 1, "type": "魚"},
]

days = ["月", "火", "水", "木", "金", "土", "日"]

# -----------------------------
# 通常の献立生成
# -----------------------------
@app.get("/menu")
def get_menu():
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

    shopping = list(set(
        ing for m in menus for ing in m["ingredients"]
    ))

    return {
        "days": week,
        "shopping": shopping,
        "nutrition": {
            "veg_score": veg_total,
            "fish_count": fish_count
        }
    }

# -----------------------------
# 在庫リクエスト用
# -----------------------------
class StockRequest(BaseModel):
    stock: list[str]

# -----------------------------
# 在庫から献立生成
# -----------------------------
@app.post("/menu_from_stock")
def menu_from_stock(req: StockRequest):
    stock = req.stock

    # マッチ数で評価
    scored = []
    for m in menus:
        match = sum(1 for s in stock if s in m["ingredients"])
        scored.append((m, match))

    # マッチ多い順
    scored.sort(key=lambda x: x[1], reverse=True)

    # 上位だけ使う（0マッチ排除）
    filtered = [m for m, score in scored if score > 0]

    if not filtered:
        filtered = menus

    week = []
    veg_total = 0
    fish_count = 0
    needed_ingredients = set()

    for i in range(7):
        m = random.choice(filtered)

        week.append({
            "day": days[i],
            "menu": m["name"]
        })

        veg_total += m["veg"]
        if m["type"] == "魚":
            fish_count += 1

        # 足りない食材
        missing = set(m["ingredients"]) - set(stock)
        needed_ingredients.update(missing)

    return {
        "days": week,
        "shopping": list(needed_ingredients),
        "nutrition": {
            "veg_score": veg_total,
            "fish_count": fish_count
        }
    }
