import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.store import FoodPrice, Store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["store"])


class StoreCreate(BaseModel):
    name: str
    type: str = "supermarket"


class StoreRead(BaseModel):
    id: int
    name: str
    type: str
    model_config = {"from_attributes": True}


class FoodPriceCreate(BaseModel):
    food_id: int
    store_id: int
    price: float
    unit_size: float
    unit_id: int | None = None
    on_sale: bool = False


class FoodPriceRead(BaseModel):
    id: int
    food_id: int
    store_id: int
    price: float
    unit_size: float
    unit_id: int | None
    date_recorded: date | None
    on_sale: bool
    unit_cost: float
    model_config = {"from_attributes": True}


@router.post("/stores", response_model=StoreRead)
def create_store(data: StoreCreate, session: Session = Depends(get_session)):
    store = Store(name=data.name, type=data.type)
    session.add(store)
    session.commit()
    session.refresh(store)
    return store


@router.get("/stores", response_model=list[StoreRead])
def list_stores(session: Session = Depends(get_session)):
    return session.query(Store).order_by(Store.name).all()


@router.post("/prices", response_model=FoodPriceRead)
def add_price(data: FoodPriceCreate, session: Session = Depends(get_session)):
    price = FoodPrice(
        food_id=data.food_id,
        store_id=data.store_id,
        price=data.price,
        unit_size=data.unit_size,
        unit_id=data.unit_id,
        date_recorded=date.today(),
        on_sale=data.on_sale,
    )
    session.add(price)
    session.commit()
    session.refresh(price)
    return price


@router.get("/prices/{food_id}", response_model=list[FoodPriceRead])
def get_prices_for_food(food_id: int, session: Session = Depends(get_session)):
    return (
        session.query(FoodPrice)
        .filter(FoodPrice.food_id == food_id)
        .order_by(FoodPrice.date_recorded.desc())
        .all()
    )
