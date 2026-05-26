import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.food import Tag
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep
from app.schemas.recipe import RecipeCreate, RecipeRead

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recipe"])


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:80]


@router.post("/recipes", response_model=RecipeRead)
def create_recipe(data: RecipeCreate, session: Session = Depends(get_session)):
    recipe = Recipe(
        name=data.name,
        slug=_slugify(data.name),
        source_url=data.source_url,
        servings=data.servings,
        servings_text=data.servings_text,
        prep_time=data.prep_time,
        cook_time=data.cook_time,
        type=getattr(data, 'type', 'main') or 'main',
        freeze_method=getattr(data, 'freeze_method', None),
        freeze_shelf_life_days=data.freezer_shelf_life_days,
    )
    session.add(recipe)
    session.flush()

    for i, ing in enumerate(data.ingredients):
        session.add(RecipeIngredient(
            recipe_id=recipe.id,
            food_id=ing.food_id,
            unit_id=ing.unit_id,
            quantity=ing.quantity,
            note=ing.note,
            original_text=ing.original_text,
            position=ing.position or i,
        ))

    for i, step in enumerate(data.steps):
        session.add(RecipeStep(
            recipe_id=recipe.id,
            text=step.text,
            position=step.position or i,
            duration_minutes=step.duration_minutes,
        ))

    if data.tag_ids:
        tags = session.query(Tag).filter(Tag.id.in_(data.tag_ids)).all()
        recipe.tags = tags

    session.commit()
    session.refresh(recipe)
    log.info("Created recipe: %s (id=%d, servings=%d)", recipe.name, recipe.id, recipe.servings)
    return recipe


@router.get("/recipes", response_model=list[RecipeRead])
def list_recipes(session: Session = Depends(get_session)):
    return session.query(Recipe).order_by(Recipe.name).all()


@router.get("/recipes/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    return recipe


@router.put("/recipes/{recipe_id}", response_model=RecipeRead)
def update_recipe(recipe_id: int, data: RecipeCreate, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    log.info("Updating recipe id=%d name=%s ingredients=%d steps=%d",
             recipe_id, data.name, len(data.ingredients), len(data.steps))

    recipe.name = data.name
    recipe.slug = _slugify(data.name)
    recipe.source_url = data.source_url
    recipe.servings = data.servings
    recipe.servings_text = data.servings_text
    recipe.prep_time = data.prep_time
    recipe.cook_time = data.cook_time
    recipe.type = data.type or "main"
    recipe.freeze_method = data.freeze_method
    recipe.freeze_shelf_life_days = data.freezer_shelf_life_days

    for ing in list(recipe.ingredients):
        session.delete(ing)
    for step in list(recipe.steps):
        session.delete(step)
    session.flush()

    for i, ing in enumerate(data.ingredients):
        session.add(RecipeIngredient(
            recipe_id=recipe.id,
            food_id=ing.food_id,
            unit_id=ing.unit_id,
            quantity=ing.quantity,
            note=ing.note,
            original_text=ing.original_text,
            position=ing.position or i,
        ))

    for i, step in enumerate(data.steps):
        session.add(RecipeStep(
            recipe_id=recipe.id,
            text=step.text,
            position=step.position or i,
            duration_minutes=step.duration_minutes,
        ))

    if data.tag_ids:
        tags = session.query(Tag).filter(Tag.id.in_(data.tag_ids)).all()
        recipe.tags = tags

    session.commit()
    session.refresh(recipe)
    return recipe


@router.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    session.delete(recipe)
    session.commit()
    return {"deleted": recipe_id}
