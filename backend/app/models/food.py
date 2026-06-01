from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FoodCategory(Base):
    __tablename__ = "food_categories"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    foods: Mapped[list[Food]] = relationship("Food", back_populates="category")

    def __repr__(self) -> str:
        return f"<FoodCategory {self.name}>"


class Food(Base):
    __tablename__ = "foods"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    plural_name: Mapped[str | None] = mapped_column(String)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("food_categories.id"))
    default_unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    default_shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    freezer_shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    is_staple: Mapped[bool] = mapped_column(Boolean, default=False)
    is_prepackaged_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    # V3: 常溫長放（罐頭、乾貨、醬料）→ 可一次買多啲囤；否則買 2-3 日份
    is_shelf_stable: Mapped[bool] = mapped_column(Boolean, default=False)
    # V3: 建議去邊間鋪買（亞洲嘢 T&T / 西式平貨 Walmart）
    preferred_store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    store_reason: Mapped[str | None] = mapped_column(String)

    category: Mapped[FoodCategory | None] = relationship("FoodCategory", back_populates="foods")
    default_unit: Mapped[Unit | None] = relationship("Unit", foreign_keys=[default_unit_id])
    preferred_store: Mapped["Store | None"] = relationship("Store", foreign_keys=[preferred_store_id])
    aliases: Mapped[list[FoodAlias]] = relationship("FoodAlias", back_populates="food", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Food {self.name}>"


class FoodAlias(Base):
    __tablename__ = "food_aliases"

    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    food: Mapped[Food] = relationship("Food", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<FoodAlias {self.name} → {self.food_id}>"


class Unit(Base):
    __tablename__ = "units"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    abbreviation: Mapped[str | None] = mapped_column(String)
    standard_quantity: Mapped[float | None] = mapped_column(Float)
    standard_unit: Mapped[str | None] = mapped_column(String)

    aliases: Mapped[list[UnitAlias]] = relationship("UnitAlias", back_populates="unit", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Unit {self.name}>"


class UnitAlias(Base):
    __tablename__ = "unit_aliases"

    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    unit: Mapped[Unit] = relationship("Unit", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<UnitAlias {self.name} → {self.unit_id}>"


class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Tag {self.type}:{self.name}>"


recipe_tags = Table(
    "recipe_tags",
    Base.metadata,
    Column("recipe_id", Integer, ForeignKey("recipes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

RecipeTag = recipe_tags


class FoodSubstitution(Base):
    """XO醬代蒜蓉+小米辣：一個 food 可以被另一個代替。"""
    __tablename__ = "food_substitutions"

    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    substitute_food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    ratio: Mapped[float] = mapped_column(Float, default=1.0)
    note: Mapped[str | None] = mapped_column(String)

    food: Mapped[Food] = relationship("Food", foreign_keys=[food_id])
    substitute: Mapped[Food] = relationship("Food", foreign_keys=[substitute_food_id])
