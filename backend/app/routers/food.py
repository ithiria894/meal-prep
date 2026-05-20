import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.food import Food, FoodAlias, FoodCategory, Unit, UnitAlias, Tag
from app.schemas.food import (
    FoodCategoryCreate, FoodCategoryRead,
    FoodCreate, FoodRead,
    UnitCreate, UnitRead,
    TagCreate, TagRead,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["food"])


@router.post("/categories", response_model=FoodCategoryRead)
def create_category(data: FoodCategoryCreate, session: Session = Depends(get_session)):
    cat = FoodCategory(name=data.name, sort_order=data.sort_order)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@router.get("/categories", response_model=list[FoodCategoryRead])
def list_categories(session: Session = Depends(get_session)):
    return session.query(FoodCategory).order_by(FoodCategory.sort_order).all()


@router.post("/foods", response_model=FoodRead)
def create_food(data: FoodCreate, session: Session = Depends(get_session)):
    food = Food(
        name=data.name,
        plural_name=data.plural_name,
        category_id=data.category_id,
        default_unit_id=data.default_unit_id,
        default_shelf_life_days=data.default_shelf_life_days,
        freezer_shelf_life_days=data.freezer_shelf_life_days,
        is_staple=data.is_staple,
    )
    session.add(food)
    session.flush()

    for alias_name in data.aliases:
        session.add(FoodAlias(food_id=food.id, name=alias_name))

    session.commit()
    session.refresh(food)
    log.info("Created food: %s (id=%d)", food.name, food.id)
    return food


@router.get("/foods", response_model=list[FoodRead])
def list_foods(session: Session = Depends(get_session)):
    return session.query(Food).order_by(Food.name).all()


@router.get("/foods/{food_id}", response_model=FoodRead)
def get_food(food_id: int, session: Session = Depends(get_session)):
    food = session.get(Food, food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    return food


@router.post("/units", response_model=UnitRead)
def create_unit(data: UnitCreate, session: Session = Depends(get_session)):
    unit = Unit(
        name=data.name,
        abbreviation=data.abbreviation,
        standard_quantity=data.standard_quantity,
        standard_unit=data.standard_unit,
    )
    session.add(unit)
    session.flush()

    for alias_name in data.aliases:
        session.add(UnitAlias(unit_id=unit.id, name=alias_name))

    session.commit()
    session.refresh(unit)
    return unit


@router.get("/units", response_model=list[UnitRead])
def list_units(session: Session = Depends(get_session)):
    return session.query(Unit).order_by(Unit.name).all()


@router.post("/tags", response_model=TagRead)
def create_tag(data: TagCreate, session: Session = Depends(get_session)):
    tag = Tag(name=data.name, type=data.type)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.get("/tags", response_model=list[TagRead])
def list_tags(session: Session = Depends(get_session)):
    return session.query(Tag).order_by(Tag.type, Tag.name).all()


@router.patch("/foods/{food_id}")
def update_food(food_id: int, data: FoodCreate, session: Session = Depends(get_session)):
    food = session.get(Food, food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    food.name = data.name
    food.plural_name = data.plural_name
    food.category_id = data.category_id
    food.default_unit_id = data.default_unit_id
    food.default_shelf_life_days = data.default_shelf_life_days
    food.freezer_shelf_life_days = data.freezer_shelf_life_days
    food.is_staple = data.is_staple
    session.commit()
    return food


@router.delete("/foods/{food_id}")
def delete_food(food_id: int, session: Session = Depends(get_session)):
    food = session.get(Food, food_id)
    if not food:
        raise HTTPException(404, "Food not found")
    session.delete(food)
    session.commit()
    return {"deleted": food_id}
