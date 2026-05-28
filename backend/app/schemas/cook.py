from datetime import datetime
from pydantic import BaseModel


class CookLogCreate(BaseModel):
    recipe_id: int
    servings_cooked: int | None = None
    bump_favorite: bool = True
    notes: str | None = None
    cooked_at: datetime | None = None


class ConsumedItem(BaseModel):
    food_id: int
    food_name: str
    requested: float
    consumed: float
    deficit: float


class CookLogResult(BaseModel):
    recipe_id: int
    recipe_name: str
    servings_cooked: int
    scale_factor: float
    consumed: list[ConsumedItem]
    favorite_weight: int | None
    cooked_at: datetime


class CookHistoryEntry(BaseModel):
    recipe_id: int
    recipe_name: str
    cooked_at: datetime
    ingredient_count: int
