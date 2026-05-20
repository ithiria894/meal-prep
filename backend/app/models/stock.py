from __future__ import annotations

from datetime import date
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Location(Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<Location {self.name} ({self.type})>"


class StockEntry(Base):
    __tablename__ = "stock_entries"

    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    best_before_date: Mapped[date | None] = mapped_column(Date)
    purchased_date: Mapped[date | None] = mapped_column(Date)
    price: Mapped[float | None] = mapped_column(Float)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    batch_id: Mapped[str | None] = mapped_column(String)
    is_exhausted: Mapped[bool] = mapped_column(Boolean, default=False)

    food: Mapped["Food"] = relationship("Food")
    location: Mapped[Location] = relationship("Location")
    unit: Mapped["Unit | None"] = relationship("Unit")
    store: Mapped["Store | None"] = relationship("Store")

    def __repr__(self) -> str:
        return f"<StockEntry {self.food_id} ×{self.amount} @ {self.location_id}>"


class StockLog(Base):
    __tablename__ = "stock_log"

    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    related_recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"))
    batch_id: Mapped[str | None] = mapped_column(String)

    food: Mapped["Food"] = relationship("Food")
    unit: Mapped["Unit | None"] = relationship("Unit")

    def __repr__(self) -> str:
        return f"<StockLog {self.transaction_type} {self.food_id} ×{self.amount}>"


class FreezerPortion(Base):
    __tablename__ = "freezer_portions"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    recipe_name: Mapped[str] = mapped_column(String, nullable=False)

    portion_type: Mapped[str] = mapped_column(String, nullable=False, default="souper_cube")
    component_name: Mapped[str | None] = mapped_column(String)

    cube_count: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed_count: Mapped[int] = mapped_column(Integer, default=0)
    date_prepared: Mapped[date] = mapped_column(Date, nullable=False)
    best_before_date: Mapped[date | None] = mapped_column(Date)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    cost_per_cube: Mapped[float | None] = mapped_column(Float)

    cooking_instructions: Mapped[str | None] = mapped_column(Text)

    recipe: Mapped["Recipe"] = relationship("Recipe")
    location: Mapped[Location | None] = relationship("Location")

    @property
    def remaining(self) -> int:
        return self.cube_count - self.consumed_count

    def __repr__(self) -> str:
        return f"<FreezerPortion {self.recipe_name} ({self.portion_type}) {self.remaining}/{self.cube_count}>"
