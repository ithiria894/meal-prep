import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.favorites import FavoriteRecipe
from app.models.weekly_specials import WeeklySpecial
from app.services.auto_planner import suggest_weekly_plan, find_unmatched_specials

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["planner"])


class FavoriteAdd(BaseModel):
    recipe_id: int
    frequency_weight: int = 1


class FavoriteRead(BaseModel):
    id: int
    recipe_id: int
    frequency_weight: int
    model_config = {"from_attributes": True}


class SpecialAdd(BaseModel):
    name: str
    price: float
    original_price: float | None = None
    discount_pct: int | None = None
    unit: str | None = None
    food_id: int | None = None
    store_id: int | None = None


class PlanSuggestion(BaseModel):
    recipe_id: int
    recipe_name: str
    score: float
    is_favorite: bool
    on_sale_ingredients: int
    pantry_ingredients: int
    new_ingredients_needed: int
    freezable: bool
    planned_servings: int


@router.post("/favorites", response_model=FavoriteRead)
def add_favorite(data: FavoriteAdd, session: Session = Depends(get_session)):
    existing = session.query(FavoriteRecipe).filter(
        FavoriteRecipe.recipe_id == data.recipe_id
    ).first()
    if existing:
        existing.frequency_weight = data.frequency_weight
        session.commit()
        session.refresh(existing)
        return existing

    fav = FavoriteRecipe(
        user_preferences_id=1,
        recipe_id=data.recipe_id,
        frequency_weight=data.frequency_weight,
    )
    session.add(fav)
    session.commit()
    session.refresh(fav)
    return fav


@router.get("/favorites", response_model=list[FavoriteRead])
def list_favorites(session: Session = Depends(get_session)):
    return session.query(FavoriteRecipe).all()


@router.delete("/favorites/{recipe_id}")
def remove_favorite(recipe_id: int, session: Session = Depends(get_session)):
    fav = session.query(FavoriteRecipe).filter(
        FavoriteRecipe.recipe_id == recipe_id
    ).first()
    if fav:
        session.delete(fav)
        session.commit()
    return {"removed": recipe_id}


@router.post("/specials")
def add_specials(data: list[SpecialAdd], session: Session = Depends(get_session)):
    added = 0
    for item in data:
        special = WeeklySpecial(
            name=item.name,
            price=item.price,
            original_price=item.original_price,
            discount_pct=item.discount_pct,
            unit=item.unit,
            food_id=item.food_id,
            store_id=item.store_id,
        )
        session.add(special)
        added += 1
    session.commit()
    return {"added": added}


@router.get("/specials")
def list_specials(session: Session = Depends(get_session)):
    specials = session.query(WeeklySpecial).all()
    return [{
        "id": s.id,
        "name": s.name,
        "price": s.price,
        "original_price": s.original_price,
        "discount_pct": s.discount_pct,
        "food_id": s.food_id,
        "matched": s.matched,
        "savings": s.savings,
    } for s in specials]


@router.get("/suggest-plan", response_model=list[PlanSuggestion])
def suggest_plan(
    num_meals: int = 10,
    max_same_dish: int = 3,
    session: Session = Depends(get_session),
):
    return suggest_weekly_plan(session, num_meals, max_same_dish)


@router.get("/suggest-plan/unmatched")
def unmatched_specials(session: Session = Depends(get_session)):
    return find_unmatched_specials(session)
