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
    required_ingredients: List[str] = Field(default_factory=list)


class RecalculateRequest(BaseModel):
    menu: List[Dict[str, Any]]
    store: str = "ロピア"
    required_ingredients: List[str] = Field(default_factory=list)


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


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    menu = payload.get("menu")
    if not isinstance(menu, list):
        raise ValueError("menu must be a list")

    normalized_menu = []
    generated_items = []

    for idx, day in enumerate(menu[:7]):
        if not isinstance(day, dict):
            day = {}
        main = normalize_recipe(day.get("main"))
        side = normalize_recipe(day.get("side"))
        lunch = normalize_recipe(day.get("lunch"))

        generated_items.extend(main["ingredients"])
        generated_items.extend(side["ingredients"])

        normalized_menu.append(
            {
                "day": clean_text(day.get("day")) or f"{idx + 1}日目",
                "type": clean_text(day.get("type")) or "未分類",
                "main": main,
                "side": side,
                "lunch": lunch,
            }
        )

    raw_shopping = payload.get("shopping_list")
    shopping_source = raw_shopping if isinstance(raw_shopping, list) and raw_shopping else generated_items

    return {
        "usage_tips": clean_text(payload.get("usage_tips")),
        "menu": normalized_menu,
        "shopping_list": merge_items(shopping_source),
    }


def parse_gemini_json(text: str) -> Dict[str, Any]:
    cleaned = clean_text(text)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def extract_gemini_text(response: requests.Response) -> str:
    if not response.ok:
        logger.error("Gemini API error %s: %s", response.status_code, response.text[:1000])
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error {response.status_code}: {response.text[:300]}",
        )

    gemini_body = response.json()
    candidates = gemini_body.get("candidates") or []
    if not candidates:
        logger.error("Gemini returned no candidates: %s", json.dumps(gemini_body, ensure_ascii=False)[:1000])
        raise HTTPException(status_code=502, detail="Gemini returned no candidates")

    parts = candidates[0].get("content", {}).get("parts") or []
    text = next((part.get("text") for part in parts if part.get("text")), "")
    if not text:
        logger.error("Gemini returned no text parts: %s", json.dumps(gemini_body, ensure_ascii=False)[:1000])
        raise HTTPException(status_code=502, detail="Gemini returned no text")

    return text


def call_gemini_json(prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_API_KEY}"
    response = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": temperature,
            },
        },
        timeout=60,
    )
    return parse_gemini_json(extract_gemini_text(response))


def build_prompt(req: MenuRequest) -> str:
    rejected = "、".join(req.rejected_menus) if req.rejected_menus else "なし"
    required = "、".join(req.required_ingredients) if req.required_ingredients else "なし"
    store_rule = (
        "ロピア: 大容量肉（みなもと牛・豚）、自社製タレ、モンスターバーガー等のデカ盛り惣菜、冷凍ピザを活用。"
        if req.store == "ロピア"
        else "業務スーパー: 1kg惣菜、冷凍野菜、パウチ煮物、皿うどん、冷凍揚げ物、直輸入パスタソースを活用。"
    )

    return f"""
あなたは献立生成アプリ「Kon-Date」の献立エンジンです。
モデルは gemini-2.5-flash 固定です。4人家族（食べ盛り含む）向けに、指定店舗の強みを活かした1週間分の献立を作ってください。

店舗: {req.store}
店舗ルール: {store_rule}
除外する料理: {rejected}
必須食材: {required}

必須ルール:
- 既製品ベース3日、簡単料理2日、本格料理2日。
- 揚げ物は週1回以内。
- エビ、カニ、タコ、イカは絶対に使わない。
- 既製品使用時は包装裏面に一般的に記載される分量・手順に沿う。
- 各日ごとに main, side, lunch を必ず入れる。
- lunch は既製品ベースまたは超簡単なものにする。
- 必須食材が「なし」以外の場合、主菜・副菜・昼食のいずれかに自然な形で週3回以上登場させる。
- 必須食材は買い物リストと各料理の ingredients に必ず反映する。
- 1週間の食材購入金額は、在庫品を除く買い足し分としておおよそ2万円前後に収まるようにする。
- 高額食材に偏らせず、大容量品・冷凍品・既製品を活用して満足度と予算のバランスを取る。
- usage_tips は栄養バランススコアと短いコメントを合計3行以内で書く。

出力はJSONだけにしてください。Markdownや説明文は不要です。
各 main / side / lunch には recipe とは別に ingredients 配列を必ず入れてください。
ingredients は買い物リスト再計算に使うため、item, amount, unit を必ず持つ数値データにしてください。

形式:
{{
  "usage_tips": "栄養バランス: 82点\\n既製品を使いつつ野菜量を確保。\\n昼は軽めで夕食と重複しにくい構成。",
  "menu": [
    {{
      "day": "月",
      "type": "既製品ベース",
      "main": {{
        "name": "料理名",
        "recipe": "- 材料名: 1 個\\n手順...",
        "ingredients": [{{"item": "材料名", "amount": 1, "unit": "個"}}]
      }},
      "side": {{
        "name": "料理名",
        "recipe": "- 材料名: 200 g\\n手順...",
        "ingredients": [{{"item": "材料名", "amount": 200, "unit": "g"}}]
      }},
      "lunch": {{
        "name": "料理名",
        "recipe": "- 材料名: 2 袋\\n手順...",
        "ingredients": [{{"item": "材料名", "amount": 2, "unit": "袋"}}]
      }}
    }}
  ],
  "shopping_list": [{{"item": "材料名", "amount": 1, "unit": "個"}}]
}}
"""


def build_recalculate_prompt(req: RecalculateRequest) -> str:
    required = "、".join(req.required_ingredients) if req.required_ingredients else "なし"
    menu_json = json.dumps(req.menu, ensure_ascii=False)

    return f"""
あなたは献立生成アプリ「Kon-Date」の買い物リスト集計エンジンです。
以下の1週間献立JSONを読み、4人家族向けの買い物リスト合計を再計算してください。

店舗: {req.store}
必須食材: {required}

集計ルール:
- 各日の main と side の ingredients を通常1.0倍で合計する。
- isNextDayMade が true の日は、その日の main と side を2.0倍で合計する。
- type が「前日の残り」の日は、夕食の main と side は買い物リストに加算しない。
- noMeal が true または type が「食事なし」の日は、その日の main, side, lunch をすべて買い物リストに加算しない。
- showLunch が true の日は、その日の lunch の ingredients を0.5倍で合計する。
- replacedOriginal は、前日の残りに置き換わる前の献立情報なので、買い物リストには加算しない。
- 同じ item かつ同じ unit は必ず合算する。
- amount は数値にし、小数1桁までに丸める。
- エビ、カニ、タコ、イカが含まれる場合は除外する。
- 必須食材が「なし」以外の場合、献立内に含まれている必須食材の量を漏れなく合計する。
- 合計金額が1週間でおおよそ2万円前後になるよう、数量を現実的に調整する。ただし献立に必要な食材は不足させない。

出力はJSONだけにしてください。形式:
{{
  "shopping_list": [
    {{"item": "材料名", "amount": 1.5, "unit": "個"}}
  ]
}}

献立JSON:
{menu_json}
"""


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Kon-Date API", "model": MODEL_ID}


@app.post("/generate_menu")
def generate_menu(req: MenuRequest):
    try:
        payload = call_gemini_json(build_prompt(req), temperature=0.7)
        return normalize_payload(payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gemini response handling failed")
        raise HTTPException(status_code=502, detail=f"Gemini response handling failed: {exc}") from exc


@app.post("/recalculate_shopping_list")
def recalculate_shopping_list(req: RecalculateRequest):
    try:
        payload = call_gemini_json(build_recalculate_prompt(req), temperature=0.1)
        raw_items = payload.get("shopping_list") if isinstance(payload, dict) else []
        if not isinstance(raw_items, list):
            raise ValueError("shopping_list must be a list")
        return {"shopping_list": merge_items(raw_items)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gemini shopping list recalculation failed")
        raise HTTPException(status_code=502, detail=f"Gemini shopping list recalculation failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
