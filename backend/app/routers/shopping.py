import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.shopping import ShoppingList, ShoppingListItem
from app.schemas.shopping import CheckItemRequest, ShoppingListRead
from app.services.shopping_aggregator import generate_shopping_list

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["shopping"])


@router.post("/shopping-lists/generate/{plan_id}", response_model=ShoppingListRead)
def generate(plan_id: int, session: Session = Depends(get_session)):
    shopping_list = generate_shopping_list(session, plan_id)
    return shopping_list


@router.get("/shopping-lists", response_model=list[ShoppingListRead])
def list_shopping_lists(session: Session = Depends(get_session)):
    return session.query(ShoppingList).order_by(ShoppingList.created_at.desc()).all()


@router.get("/shopping-lists/{list_id}", response_model=ShoppingListRead)
def get_shopping_list(list_id: int, session: Session = Depends(get_session)):
    sl = session.get(ShoppingList, list_id)
    if not sl:
        raise HTTPException(404, "Shopping list not found")
    return sl


@router.patch("/shopping-lists/items/{item_id}/check")
def check_item(item_id: int, data: CheckItemRequest, session: Session = Depends(get_session)):
    item = session.get(ShoppingListItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.checked = data.checked
    session.commit()
    return {"id": item_id, "checked": item.checked}
