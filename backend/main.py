import json
import logging
import os
import re
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI()
logger = logging.getLogger("kon_date")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash"


class MenuRequest(BaseModel):
    store: str
    rejected_menus: List[str] = Field(default_factory=list)


def to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0.0


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def parse_ingredients_from_recipe(recipe: str) -> List[Dict[str, Any]]:
    ingredients = []
    for line in clean_text(recipe).splitlines():
        match = re.match(r"^\s*[-・]?\s*([^:：\d]+?)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*([^\s、,。]*)", line)
        if not match:
            continue
        item = clean_text(match.group(1))
        amount = to_float(match.group(2))
        unit = clean_text(match.group(3))
        if item and amount > 0:
            ingredients.append({"item": item, "amount": amount, "unit": unit})
    return ingredients


def normalize_recipe(recipe_obj: Any) -> Dict[str, Any]:
    if not isinstance(recipe_obj, dict):
        recipe_obj = {}

    normalized = {
        "name": clean_text(recipe_obj.get("name")) or "未設定",
        "recipe": clean_text(recipe_obj.get("recipe")),
    }

    raw_ingredients = recipe_obj.get("ingredients")
    if isinstance(raw_ingredients, list):
        ingredients = [
            {
                "item": clean_text(i.get("item") or i.get("name")),
                "amount": to_float(i.get("amount")),
                "unit": clean_text(i.get("unit")),
            }
            for i in raw_ingredients
            if isinstance(i, dict)
        ]
        ingredients = [i for i in ingredients if i["item"] and i["amount"] > 0]
    else:
        ingredients = parse_ingredients_from_recipe(normalized["recipe"])

    normalized["ingredients"] = ingredients
    return normalized


def merge_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for raw in items:
        item = clean_text(raw.get("item") or raw.get("name"))
        unit = clean_text(raw.get("unit"))
        amount = to_float(raw.get("amount"))
        if not item or amount <= 0:
            continue
        key = f"{item}__{unit}"
        current = merged.setdefault(key, {"item": item, "amount": 0.0, "unit": unit})
        current["amount"] = round(current["amount"] + amount, 1)
    return list(merged.values())
