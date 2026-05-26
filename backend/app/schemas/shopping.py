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


class ShoppingListCreate(BaseModel):
    status: str = "draft"


class ShoppingListItemCreate(BaseModel):
    food_id: int | None = None
    unit_id: int | None = None
    quantity: float = 1
    category_id: int | None = None
    estimated_cost: float | None = None
    store_id: int | None = None
    note: str | None = None
