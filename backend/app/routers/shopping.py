import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.food import Food
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.store import Store
from app.schemas.shopping import (
    CheckItemRequest,
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListRead,
)
from app.services.shopping_aggregator import generate_shopping_list

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["shopping"])


@router.post("/shopping-lists/generate/{plan_id}", response_model=ShoppingListRead)
def generate(plan_id: int, session: Session = Depends(get_session)):
    shopping_list = generate_shopping_list(session, plan_id)
    return shopping_list


@router.post("/shopping-lists", response_model=ShoppingListRead)
def create_shopping_list(data: ShoppingListCreate, session: Session = Depends(get_session)):
    sl = ShoppingList(meal_plan_id=None, status=data.status)
    session.add(sl)
    session.commit()
    session.refresh(sl)
    log.info("Created manual shopping list id=%d status=%s", sl.id, sl.status)
    return sl


@router.post("/shopping-lists/{list_id}/items", response_model=ShoppingListRead)
def add_item(list_id: int, data: ShoppingListItemCreate, session: Session = Depends(get_session)):
    sl = session.get(ShoppingList, list_id)
    if not sl:
        raise HTTPException(404, "Shopping list not found")

    item = ShoppingListItem(
        shopping_list_id=list_id,
        food_id=data.food_id,
        unit_id=data.unit_id,
        quantity=data.quantity,
        category_id=data.category_id,
        estimated_cost=data.estimated_cost,
        store_id=data.store_id,
    )
    session.add(item)
    session.commit()
    session.refresh(sl)
    log.info("Added item to shopping list %d: food_id=%s qty=%s", list_id, data.food_id, data.quantity)
    return sl


@router.delete("/shopping-lists/items/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(ShoppingListItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    session.delete(item)
    session.commit()
    return {"deleted": item_id}


@router.get("/shopping-lists", response_model=list[ShoppingListRead])
def list_shopping_lists(session: Session = Depends(get_session)):
    return session.query(ShoppingList).order_by(ShoppingList.created_at.desc()).all()


@router.get("/shopping-lists/{list_id}", response_model=ShoppingListRead)
def get_shopping_list(list_id: int, session: Session = Depends(get_session)):
    sl = session.get(ShoppingList, list_id)
    if not sl:
        raise HTTPException(404, "Shopping list not found")
    return sl


@router.get("/shopping-lists/{list_id}/by-store")
def get_shopping_list_by_store(list_id: int, session: Session = Depends(get_session)):
    """Group shopping list items by preferred store (T&T / Walmart / 未分類)."""
    sl = session.get(ShoppingList, list_id)
    if not sl:
        raise HTTPException(404, "Shopping list not found")
    grouped: dict[str, list] = {}
    for item in sl.items:
        store_name = "未分類"
        if item.food_id:
            food = session.get(Food, item.food_id)
            if food and food.preferred_store_id:
                store = session.get(Store, food.preferred_store_id)
                if store:
                    store_name = store.name
        grouped.setdefault(store_name, []).append({
            "id": item.id,
            "food_id": item.food_id,
            "quantity": item.quantity,
            "unit_id": item.unit_id,
            "checked": item.checked,
            "estimated_cost": item.estimated_cost,
        })
    log.info("Shopping list %d grouped into %d stores", list_id, len(grouped))
    return grouped


@router.patch("/shopping-lists/items/{item_id}/check")
def check_item(item_id: int, data: CheckItemRequest, session: Session = Depends(get_session)):
    item = session.get(ShoppingListItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.checked = data.checked
    session.commit()
    return {"id": item_id, "checked": item.checked}
