from pydantic import BaseModel


class RecipeIngredientCreate(BaseModel):
    food_id: int | None = None
    unit_id: int | None = None
    quantity: float | None = None
    note: str | None = None
    original_text: str | None = None
    position: int = 0


class RecipeIngredientRead(BaseModel):
    id: int
    food_id: int | None
    unit_id: int | None
    quantity: float | None
    note: str | None
    original_text: str | None
    position: int
    model_config = {"from_attributes": True}


class RecipeStepCreate(BaseModel):
    text: str
    position: int = 0
    duration_minutes: int | None = None


class RecipeStepRead(BaseModel):
    id: int
    position: int
    text: str
    duration_minutes: int | None
    model_config = {"from_attributes": True}


class RecipeCreate(BaseModel):
    name: str
    source_url: str | None = None
    servings: int = 1
    servings_text: str | None = None
    prep_time: int | None = None
    cook_time: int | None = None
    type: str = "main"
    freeze_method: str | None = None
    freezer_shelf_life_days: int | None = None
    ingredients: list[RecipeIngredientCreate] = []
    steps: list[RecipeStepCreate] = []
    tag_ids: list[int] = []


class RecipeRead(BaseModel):
    id: int
    name: str
    slug: str | None
    source_url: str | None
    servings: int
    servings_text: str | None
    prep_time: int | None
    cook_time: int | None
    type: str
    freeze_method: str | None
    freeze_shelf_life_days: int | None
    freeze_notes: str | None
    is_builtin: bool
    ingredients: list[RecipeIngredientRead] = []
    steps: list[RecipeStepRead] = []
    model_config = {"from_attributes": True}
