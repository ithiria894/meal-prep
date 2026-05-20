from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    meal_plan_id: Mapped[int | None] = mapped_column(ForeignKey("meal_plans.id"))
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")

    meal_plan: Mapped["MealPlan | None"] = relationship("MealPlan")
    items: Mapped[list[ShoppingListItem]] = relationship(
        "ShoppingListItem",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ShoppingList {self.status} ({len(self.items)} items)>"


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    shopping_list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"), nullable=False)
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("food_categories.id"))
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    pantry_deducted: Mapped[float] = mapped_column(Float, default=0)

    shopping_list: Mapped[ShoppingList] = relationship("ShoppingList", back_populates="items")
    food: Mapped["Food | None"] = relationship("Food")
    unit: Mapped["Unit | None"] = relationship("Unit")
    category: Mapped["FoodCategory | None"] = relationship("FoodCategory")
    store: Mapped["Store | None"] = relationship("Store")
    recipe_sources: Mapped[list[ShoppingListItemSource]] = relationship(
        "ShoppingListItemSource",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ShoppingListItem {self.food_id} ×{self.quantity}>"


class ShoppingListItemSource(Base):
    __tablename__ = "shopping_list_item_sources"

    item_id: Mapped[int] = mapped_column(ForeignKey("shopping_list_items.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    quantity_from_recipe: Mapped[float] = mapped_column(Float, nullable=False)

    item: Mapped[ShoppingListItem] = relationship("ShoppingListItem", back_populates="recipe_sources")
    recipe: Mapped["Recipe"] = relationship("Recipe")

    def __repr__(self) -> str:
        return f"<Source recipe={self.recipe_id} qty={self.quantity_from_recipe}>"
