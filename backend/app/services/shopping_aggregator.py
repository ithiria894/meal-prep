"""Pipeline 1: MealPlan + BatchCookPlan → Shopping List

Aggregates ingredients from:
1. BatchCookPlan entries (total_servings, not eat_now)
2. Any direct meal plan entries with recipe_id

Skips staples, deducts pantry stock.
All deterministic — zero AI calls.
"""

import logging
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.plan import MealPlan
from app.models.shopping import ShoppingList, ShoppingListItem, ShoppingListItemSource
from app.models.stock import StockEntry

log = logging.getLogger(__name__)


def generate_shopping_list(session: Session, meal_plan_id: int) -> ShoppingList:
    meal_plan = session.get(MealPlan, meal_plan_id)
    if not meal_plan:
        raise ValueError(f"MealPlan {meal_plan_id} not found")

    log.info("Generating shopping list for plan %s", meal_plan.week_start_date)

    aggregated: dict[tuple[int | None, int | None], dict] = defaultdict(
        lambda: {"quantity": 0.0, "sources": []}
    )

    # From batch cook plan (total_servings)
    if meal_plan.batch_cook_plan:
        for entry in meal_plan.batch_cook_plan.entries:
            recipe = entry.recipe
            scale = entry.total_servings / recipe.servings
            log.info("  Batch: %s ×%d total (eat %d, freeze %d)",
                     recipe.name, entry.total_servings, entry.eat_now_servings, entry.freeze_servings)
            _add_recipe_ingredients(aggregated, recipe, scale)

    # From direct meal plan entries (servings_wanted)
    for entry in meal_plan.entries:
        if entry.recipe_id and entry.servings_wanted and not entry.is_eating_out:
            recipe = entry.recipe
            already_in_batch = False
            if meal_plan.batch_cook_plan:
                for bc in meal_plan.batch_cook_plan.entries:
                    if bc.recipe_id == recipe.id:
                        already_in_batch = True
                        break
            if already_in_batch:
                continue

            scale = entry.servings_wanted / recipe.servings
            log.info("  Direct: %s ×%d servings", recipe.name, entry.servings_wanted)
            _add_recipe_ingredients(aggregated, recipe, scale)

    # Build shopping list
    shopping_list = ShoppingList(meal_plan_id=meal_plan_id, status="draft")
    session.add(shopping_list)
    session.flush()

    for (food_id, unit_id), data in aggregated.items():
        if food_id is None:
            continue

        food = session.get(Food, food_id)
        if not food:
            continue

        # Skip staples entirely
        if food.is_staple:
            log.info("  SKIP staple: %s", food.name)
            continue

        # V3: skip foods marked "quick-have" (user said "我有呢樣")
        if _has_quick_have(session, food_id):
            log.info("  SKIP quick-have: %s", food.name)
            continue

        total_needed = data["quantity"]
        pantry_available = _get_pantry_stock(session, food_id, unit_id)
        pantry_deducted = min(pantry_available, total_needed)
        to_buy = total_needed - pantry_deducted

        log.info("  %s: need=%.1f, pantry=%.1f, buy=%.1f",
                 food.name, total_needed, pantry_available, to_buy)

        if to_buy <= 0:
            continue

        item = ShoppingListItem(
            shopping_list_id=shopping_list.id,
            food_id=food_id,
            unit_id=unit_id,
            quantity=to_buy,
            category_id=food.category_id,
            pantry_deducted=pantry_deducted,
        )
        session.add(item)
        session.flush()

        for src in data["sources"]:
            session.add(ShoppingListItemSource(
                item_id=item.id,
                recipe_id=src["recipe_id"],
                quantity_from_recipe=src["quantity"],
            ))

    session.commit()
    log.info("Shopping list: %d items to buy", len(shopping_list.items))
    return shopping_list


def _add_recipe_ingredients(aggregated, recipe, scale):
    for ing in recipe.ingredients:
        if ing.food_id is None:
            continue
        key = (ing.food_id, ing.unit_id)
        scaled_qty = (ing.quantity or 0) * scale
        aggregated[key]["quantity"] += scaled_qty
        aggregated[key]["sources"].append({
            "recipe_id": recipe.id,
            "quantity": scaled_qty,
        })


def _has_quick_have(session: Session, food_id: int) -> bool:
    return (
        session.query(StockEntry)
        .filter(
            StockEntry.food_id == food_id,
            StockEntry.is_quick_have == True,  # noqa: E712
            StockEntry.is_exhausted == False,  # noqa: E712
        )
        .first()
    ) is not None


def _get_pantry_stock(session: Session, food_id: int, unit_id: int | None) -> float:
    entries = (
        session.query(StockEntry)
        .filter(
            StockEntry.food_id == food_id,
            StockEntry.is_exhausted == False,  # noqa: E712
        )
        .all()
    )

    total = 0.0
    for entry in entries:
        if entry.unit_id == unit_id or unit_id is None or entry.unit_id is None:
            total += entry.amount

    return total
