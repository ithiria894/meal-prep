from datetime import date
from pydantic import BaseModel


class LocationCreate(BaseModel):
    name: str
    type: str


class LocationRead(BaseModel):
    id: int
    name: str
    type: str
    model_config = {"from_attributes": True}


class StockInRequest(BaseModel):
    food_id: int
    amount: float
    location_id: int
    unit_id: int | None = None
    best_before_date: date | None = None
    price: float | None = None
    store_id: int | None = None


class QuickHaveRequest(BaseModel):
    food_id: int


class StockEntryRead(BaseModel):
    id: int
    food_id: int
    location_id: int | None
    amount: float
    unit_id: int | None
    best_before_date: date | None
    purchased_date: date | None
    price: float | None
    store_id: int | None
    batch_id: str | None
    is_exhausted: bool
    is_quick_have: bool = False
    model_config = {"from_attributes": True}


class ConsumeRequest(BaseModel):
    food_id: int
    amount: float
    unit_id: int | None = None
    recipe_id: int | None = None


class FreezerPortionRead(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str
    cube_count: int
    date_prepared: date
    best_before_date: date | None
    consumed_count: int
    cost_per_cube: float | None
    remaining: int
    model_config = {"from_attributes": True}
