from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .food import Tag, recipe_tags


class Recipe(Base):
    __tablename__ = "recipes"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    servings_text: Mapped[str | None] = mapped_column(String)
    prep_time: Mapped[int | None] = mapped_column(Integer)
    cook_time: Mapped[int | None] = mapped_column(Integer)

    type: Mapped[str] = mapped_column(String, nullable=False, default="main")
    freeze_method: Mapped[str | None] = mapped_column(String)
    freeze_shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    freeze_notes: Mapped[str | None] = mapped_column(String)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    components: Mapped[list[RecipeComponent]] = relationship(
        "RecipeComponent",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.position",
    )
    steps: Mapped[list[RecipeStep]] = relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.position",
    )
    tags: Mapped[list[Tag]] = relationship("Tag", secondary=recipe_tags)

    def __repr__(self) -> str:
        return f"<Recipe {self.name} ({self.type}, {self.servings} servings)>"


class RecipeComponent(Base):
    __tablename__ = "recipe_components"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    freeze_separately: Mapped[bool] = mapped_column(Boolean, default=False)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="components")
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient", back_populates="component"
    )

    def __repr__(self) -> str:
        return f"<RecipeComponent {self.name} (freeze_sep={self.freeze_separately})>"


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("recipe_components.id"))
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    quantity: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String)
    original_text: Mapped[str | None] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, default=0)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")
    component: Mapped[RecipeComponent | None] = relationship("RecipeComponent", back_populates="ingredients")
    food: Mapped["Food | None"] = relationship("Food")
    unit: Mapped["Unit | None"] = relationship("Unit")

    def __repr__(self) -> str:
        return f"<RecipeIngredient {self.quantity} {self.food_id}>"


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="steps")

    def __repr__(self) -> str:
        return f"<RecipeStep {self.position}>"
