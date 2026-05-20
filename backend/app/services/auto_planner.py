"""Auto meal planner — deterministic scoring, no AI.

Given: user favorites + weekly specials + pantry + budget
Output: suggested meal plan for the week

AI only needed for: "this ingredient is on sale but not in any recipe → suggest a new recipe"
Everything else is deterministic.
"""

import json
import logging
from datetime import date
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.favorites import FavoriteRecipe
from app.models.food import Food
from app.models.recipe import Recipe
from app.models.stock import StockEntry
from app.models.weekly_specials import WeeklySpecial

log = logging.getLogger(__name__)

SCORING_FILE = Path(__file__).parent.parent.parent / "data" / "scoring.json"


def _load_scoring_config() -> dict:
    if SCORING_FILE.exists():
        return json.loads(SCORING_FILE.read_text())
    return {
        "favorite_bonus": 15,
        "on_sale_ingredient_bonus": 10,
        "pantry_ingredient_bonus": 5,
        "new_ingredient_penalty": -3,
        "recent_cook_penalty": -8,
        "recent_cook_days": 3,
        "freezable_multiplier": 1.5,
        "budget_exceeded_penalty": -100,
    }


def suggest_weekly_plan(
    session: Session,
    num_meals: int = 10,
    max_same_dish: int = 3,
    budget_remaining: float | None = None,
) -> list[dict]:
    config = _load_scoring_config()

    favorites = session.query(FavoriteRecipe).all()
    favorite_ids = {f.recipe_id: f.frequency_weight for f in favorites}

    specials = (
        session.query(WeeklySpecial)
        .filter(WeeklySpecial.food_id != None)  # noqa: E711
        .all()
    )
    on_sale_food_ids = {s.food_id for s in specials}

    pantry_food_ids = set()
    for entry in session.query(StockEntry).filter(StockEntry.is_exhausted == False).all():  # noqa: E712
        pantry_food_ids.add(entry.food_id)

    all_recipes = session.query(Recipe).filter(Recipe.type == "main").all()

    scored = []
    for recipe in all_recipes:
        score = 0.0

        if recipe.id in favorite_ids:
            score += config["favorite_bonus"] * favorite_ids[recipe.id]

        recipe_food_ids = {ing.food_id for ing in recipe.ingredients if ing.food_id}

        on_sale_count = len(recipe_food_ids & on_sale_food_ids)
        score += on_sale_count * config["on_sale_ingredient_bonus"]

        pantry_count = len(recipe_food_ids & pantry_food_ids)
        score += pantry_count * config["pantry_ingredient_bonus"]

        new_count = len(recipe_food_ids - pantry_food_ids - on_sale_food_ids)
        score += new_count * config["new_ingredient_penalty"]

        if recipe.freeze_method:
            score *= config["freezable_multiplier"]

        scored.append({
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "score": round(score, 1),
            "is_favorite": recipe.id in favorite_ids,
            "on_sale_ingredients": on_sale_count,
            "pantry_ingredients": pantry_count,
            "new_ingredients_needed": new_count,
            "freezable": bool(recipe.freeze_method),
            "servings": recipe.servings,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    plan = []
    dish_count: dict[int, int] = {}
    meals_filled = 0

    for item in scored:
        if meals_filled >= num_meals:
            break

        rid = item["recipe_id"]
        if dish_count.get(rid, 0) >= max_same_dish:
            continue

        servings = min(item["servings"], num_meals - meals_filled)
        plan.append({
            **item,
            "planned_servings": servings,
        })
        dish_count[rid] = dish_count.get(rid, 0) + servings
        meals_filled += servings

    log.info("Auto plan: %d meals from %d dishes (scored %d recipes)",
             meals_filled, len(plan), len(scored))

    return plan


def find_unmatched_specials(session: Session) -> list[dict]:
    """Find specials that don't match any recipe — candidates for AI recipe suggestion."""
    specials = session.query(WeeklySpecial).filter(
        WeeklySpecial.food_id == None  # noqa: E711
    ).all()

    return [{
        "name": s.name,
        "price": s.price,
        "discount_pct": s.discount_pct,
        "original_price": s.original_price,
    } for s in specials]
