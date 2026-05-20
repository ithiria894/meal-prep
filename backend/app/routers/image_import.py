"""Image-based import endpoints.

Supports:
1. Pantry/fridge photo → AI identifies items → stock entries
2. Recipe screenshot → AI extracts recipe
3. Receipt photo → AI extracts prices (future)
"""

import base64
import json
import logging
import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.food import Food, FoodAlias
from app.models.stock import Location

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["image-import"])


class IdentifiedItem(BaseModel):
    name: str
    quantity: float | None = None
    unit: str | None = None
    food_id: int | None = None
    location_type: str | None = None
    estimated_shelf_life_days: int | None = None


class InventoryScanResult(BaseModel):
    items: list[IdentifiedItem]
    raw_ai_response: str | None = None


class InventoryScanConfirm(BaseModel):
    items: list[IdentifiedItem]
    location_id: int


def _match_food(session: Session, name: str) -> int | None:
    food = session.query(Food).filter(Food.name == name).first()
    if food:
        return food.id

    alias = session.query(FoodAlias).filter(FoodAlias.name == name).first()
    if alias:
        return alias.food_id

    for food in session.query(Food).all():
        if food.name in name or name in food.name:
            return food.id

    return None


def _image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


async def _analyze_image_openai(image_b64: str, prompt: str) -> str:
    import openai
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }],
        temperature=0.1,
        max_tokens=2000,
    )
    return resp.choices[0].message.content


@router.post("/scan/inventory", response_model=InventoryScanResult)
async def scan_inventory(
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    image_bytes = await image.read()
    image_b64 = _image_to_base64(image_bytes)

    prompt = """Look at this photo of a fridge, freezer, or pantry. Identify ALL food items visible.

Return ONLY valid JSON array:
[
  {"name": "食材名 (traditional Chinese)", "quantity": number_or_null, "unit": "unit_or_null", "location_type": "fridge/freezer/pantry", "estimated_shelf_life_days": number}
]

Be specific: "雞蛋" not "蛋類", "午餐肉" not "罐頭". Estimate quantity from what you see. Use traditional Chinese characters."""

    log.info("Scanning inventory image (%d bytes)", len(image_bytes))
    raw = await _analyze_image_openai(image_b64, prompt)

    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
    items_raw = json.loads(cleaned)

    items = []
    for item in items_raw:
        food_id = _match_food(session, item["name"])
        items.append(IdentifiedItem(
            name=item["name"],
            quantity=item.get("quantity"),
            unit=item.get("unit"),
            food_id=food_id,
            location_type=item.get("location_type"),
            estimated_shelf_life_days=item.get("estimated_shelf_life_days"),
        ))
        status = f"→ matched food_id={food_id}" if food_id else "→ NEW (will create)"
        log.info("  Found: %s ×%s %s %s", item["name"], item.get("quantity"), item.get("unit", ""), status)

    return InventoryScanResult(items=items, raw_ai_response=raw)


@router.post("/scan/inventory/confirm")
async def confirm_inventory(
    data: InventoryScanConfirm,
    session: Session = Depends(get_session),
):
    from app.services.stock_manager import stock_in

    results = []
    for item in data.items:
        food_id = item.food_id
        if not food_id:
            new_food = Food(name=item.name)
            session.add(new_food)
            session.flush()
            food_id = new_food.id
            log.info("Created new food: %s (id=%d)", item.name, food_id)

        shelf_life = item.estimated_shelf_life_days
        expiry = date.today() + timedelta(days=shelf_life) if shelf_life else None

        entry = stock_in(
            session,
            food_id=food_id,
            amount=item.quantity or 1,
            location_id=data.location_id,
            best_before_date=expiry,
        )
        results.append({"food": item.name, "food_id": food_id, "stock_entry_id": entry.id})

    return {"imported": len(results), "items": results}


@router.post("/scan/recipe")
async def scan_recipe_image(
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    image_bytes = await image.read()
    image_b64 = _image_to_base64(image_bytes)

    prompt = """Extract a recipe from this image (could be a screenshot of a cooking video, a recipe card, or handwritten recipe).

Return ONLY valid JSON:
{
  "name": "recipe name in traditional Chinese",
  "servings": 2,
  "prep_time": minutes_or_null,
  "cook_time": minutes_or_null,
  "freezable": true/false,
  "freezer_shelf_life_days": number_or_null,
  "ingredients": [
    {"name": "traditional Chinese", "quantity": number, "unit": "unit", "note": "optional"}
  ],
  "steps": [
    {"text": "step in traditional Chinese"}
  ]
}

Use traditional Chinese characters. Infer reasonable quantities if partially visible."""

    log.info("Scanning recipe image (%d bytes)", len(image_bytes))
    raw = await _analyze_image_openai(image_b64, prompt)

    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
    recipe_data = json.loads(cleaned)

    for ing in recipe_data.get("ingredients", []):
        food_id = _match_food(session, ing["name"])
        ing["food_id"] = food_id

    return {"recipe": recipe_data, "raw_ai_response": raw}
