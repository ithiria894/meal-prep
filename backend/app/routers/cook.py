import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.favorites import FavoriteRecipe
from app.models.food import Food
from app.models.recipe import Recipe
from app.models.stock import StockLog
from app.schemas.cook import (
    ConsumedItem,
    CookHistoryEntry,
    CookLogCreate,
    CookLogResult,
)
from app.services.stock_manager import consume_fifo

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["cook"])


@router.post("/cook-log", response_model=CookLogResult)
def log_cook(data: CookLogCreate, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, data.recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    servings_cooked = data.servings_cooked or recipe.servings
    if servings_cooked <= 0:
        raise HTTPException(400, "servings_cooked must be > 0")

    recipe_servings = recipe.servings or 1
    scale = servings_cooked / recipe_servings

    log.info("cook-log: recipe=%d (%s) servings=%d scale=%.3f ingredients=%d",
             recipe.id, recipe.name, servings_cooked, scale, len(recipe.ingredients))

    consumed_results: list[ConsumedItem] = []
    for ing in recipe.ingredients:
        if ing.food_id is None or ing.quantity is None:
            log.info("  skip ingredient (no food_id or quantity): %s", ing.note or ing.original_text)
            continue
        needed = ing.quantity * scale
        consumed = consume_fifo(
            session=session,
            food_id=ing.food_id,
            amount_needed=needed,
            unit_id=ing.unit_id,
            recipe_id=recipe.id,
        )
        food = session.get(Food, ing.food_id)
        consumed_results.append(ConsumedItem(
            food_id=ing.food_id,
            food_name=food.name if food else f"food_{ing.food_id}",
            requested=needed,
            consumed=consumed,
            deficit=max(0.0, needed - consumed),
        ))

    fav_weight = None
    if data.bump_favorite:
        fav = session.query(FavoriteRecipe).filter(
            FavoriteRecipe.recipe_id == recipe.id
        ).first()
        if fav:
            fav.frequency_weight += 1
            fav_weight = fav.frequency_weight
            log.info("  bumped favorite weight to %d", fav_weight)
        else:
            fav = FavoriteRecipe(
                user_preferences_id=1,
                recipe_id=recipe.id,
                frequency_weight=1,
            )
            session.add(fav)
            fav_weight = 1
            log.info("  created favorite weight=1")

    session.commit()

    return CookLogResult(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        servings_cooked=servings_cooked,
        scale_factor=scale,
        consumed=consumed_results,
        favorite_weight=fav_weight,
        cooked_at=datetime.now(timezone.utc),
    )


@router.get("/cook-log", response_model=list[CookHistoryEntry])
def list_cook_history(limit: int = 50, session: Session = Depends(get_session)):
    """List cook events grouped by recipe + timestamp from StockLog."""
    rows = (
        session.query(
            StockLog.related_recipe_id.label("recipe_id"),
            StockLog.created_at.label("cooked_at"),
            func.count(StockLog.id).label("ingredient_count"),
        )
        .filter(
            StockLog.transaction_type == "consume",
            StockLog.related_recipe_id.isnot(None),
        )
        .group_by(StockLog.related_recipe_id, StockLog.created_at)
        .order_by(StockLog.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for r in rows:
        recipe = session.get(Recipe, r.recipe_id)
        results.append(CookHistoryEntry(
            recipe_id=r.recipe_id,
            recipe_name=recipe.name if recipe else f"recipe_{r.recipe_id}",
            cooked_at=r.cooked_at,
            ingredient_count=r.ingredient_count,
        ))
    return results


@router.get("/cook-log/recipe/{recipe_id}", response_model=list[CookHistoryEntry])
def recipe_cook_history(recipe_id: int, session: Session = Depends(get_session)):
    """Get cook history for a specific recipe."""
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    rows = (
        session.query(
            StockLog.created_at.label("cooked_at"),
            func.count(StockLog.id).label("ingredient_count"),
        )
        .filter(
            StockLog.transaction_type == "consume",
            StockLog.related_recipe_id == recipe_id,
        )
        .group_by(StockLog.created_at)
        .order_by(StockLog.created_at.desc())
        .all()
    )
    return [
        CookHistoryEntry(
            recipe_id=recipe_id,
            recipe_name=recipe.name,
            cooked_at=r.cooked_at,
            ingredient_count=r.ingredient_count,
        )
        for r in rows
    ]
