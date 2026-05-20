from pydantic import BaseModel


class FoodCategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class FoodCategoryRead(BaseModel):
    id: int
    name: str
    sort_order: int
    model_config = {"from_attributes": True}


class FoodCreate(BaseModel):
    name: str
    plural_name: str | None = None
    category_id: int | None = None
    default_unit_id: int | None = None
    default_shelf_life_days: int | None = None
    freezer_shelf_life_days: int | None = None
    is_staple: bool = False
    aliases: list[str] = []


class FoodAliasRead(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class FoodRead(BaseModel):
    id: int
    name: str
    plural_name: str | None
    category_id: int | None
    default_unit_id: int | None
    default_shelf_life_days: int | None
    freezer_shelf_life_days: int | None
    is_staple: bool
    aliases: list[FoodAliasRead] = []
    model_config = {"from_attributes": True}


class UnitCreate(BaseModel):
    name: str
    abbreviation: str | None = None
    standard_quantity: float | None = None
    standard_unit: str | None = None
    aliases: list[str] = []


class UnitRead(BaseModel):
    id: int
    name: str
    abbreviation: str | None
    standard_quantity: float | None
    standard_unit: str | None
    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    type: str


class TagRead(BaseModel):
    id: int
    name: str
    type: str
    model_config = {"from_attributes": True}
