from pydantic import BaseModel


class ShoppingListItemSourceRead(BaseModel):
    recipe_id: int
    quantity_from_recipe: float
    model_config = {"from_attributes": True}


class ShoppingListItemRead(BaseModel):
    id: int
    food_id: int | None
    unit_id: int | None
    quantity: float
    checked: bool
    category_id: int | None
    estimated_cost: float | None
    store_id: int | None
    pantry_deducted: float
    recipe_sources: list[ShoppingListItemSourceRead] = []
    model_config = {"from_attributes": True}


class ShoppingListRead(BaseModel):
    id: int
    meal_plan_id: int | None
    status: str
    items: list[ShoppingListItemRead] = []
    model_config = {"from_attributes": True}


class CheckItemRequest(BaseModel):
    checked: bool = True
