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

MENU = [
    {"name": "カレー", "type": "meat", "veg": True, "soup": False},
    {"name": "シチュー", "type": "meat", "veg": True, "soup": True},
    {"name": "焼きそば", "type": "meat", "veg": False, "soup": False},
    {"name": "鍋", "type": "meat", "veg": True, "soup": True},
    {"name": "鶏の照り焼き", "type": "meat", "veg": False, "soup": False},
    {"name": "魚の塩焼き", "type": "fish", "veg": False, "soup": False},
    {"name": "冷凍餃子", "type": "meat", "veg": False, "soup": False},
    {"name": "パスタ", "type": "carb", "veg": False, "soup": False},
]

FISH_MENU = [
    {"name": "サバの塩焼き", "type": "fish", "veg": False, "soup": False},
    {"name": "鮭のムニエル", "type": "fish", "veg": False, "soup": False}
]

def nutrition_score(menu):
    meat = sum(1 for m in menu if m["type"] == "meat")
    fish = sum(1 for m in menu if m["type"] == "fish")
    veg = sum(1 for m in menu if m["veg"])
    soup = sum(1 for m in menu if m["soup"])

    score = 0

    if 4 <= meat <= 5:
        score += 3
    if 1 <= fish <= 2:
        score += 3
    if veg >= 2:
        score += 2
    if soup >= 2:
        score += 2

    return score

def generate_menu():
    return random.sample(MENU, 7)

def generate_alerts(menu):
    veg_count = sum(1 for m in menu if m["veg"])
    fish_count = sum(1 for m in menu if m["type"] == "fish")

    alerts = []

    if veg_count < 2:
        alerts.append({"type": "veg", "message": "野菜が不足しています"})

    if fish_count == 0:
        alerts.append({"type": "fish", "message": "魚料理が不足しています"})

    return alerts

def improve_menu(menu):
    fish_count = sum(1 for m in menu if m["type"] == "fish")

    if fish_count == 0:
        for i, m in enumerate(menu):
            if m["type"] == "carb":
                menu[i] = random.choice(FISH_MENU)
                break

    return menu

@app.get("/")
def root():
    return {"message": "OK"}

@app.post("/generate")
def generate():
    menu = generate_menu()
    return {
        "menu": menu,
        "score": nutrition_score(menu),
        "alerts": generate_alerts(menu)
    }

@app.post("/improve")
def improve(data: dict):
    menu = data.get("menu", [])
    improved = improve_menu(menu)
    return {
        "menu": improved,
        "score": nutrition_score(improved),
        "alerts": generate_alerts(improved)
    }