from datetime import date
from pydantic import BaseModel


class MealPlanEntryCreate(BaseModel):
    recipe_id: int
    servings_wanted: int
    date: date
    meal_type: str = "dinner"
    is_batch_cook: bool = True


class MealPlanEntryRead(BaseModel):
    id: int
    recipe_id: int
    servings_wanted: int
    date: date
    meal_type: str
    is_batch_cook: bool
    model_config = {"from_attributes": True}


class MealPlanCreate(BaseModel):
    week_start_date: date
    name: str | None = None
    entries: list[MealPlanEntryCreate] = []


class MealPlanRead(BaseModel):
    id: int
    week_start_date: date
    name: str | None
    entries: list[MealPlanEntryRead] = []
    model_config = {"from_attributes": True}
