from __future__ import annotations

from datetime import date
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Store(Base):
    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String, nullable=False, default="supermarket")

    def __repr__(self) -> str:
        return f"<Store {self.name}>"


class FoodPrice(Base):
    __tablename__ = "food_prices"

    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    unit_size: Mapped[float] = mapped_column(Float, nullable=False)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"))
    date_recorded: Mapped[date | None] = mapped_column(Date)
    on_sale: Mapped[bool] = mapped_column(Boolean, default=False)

    food: Mapped["Food"] = relationship("Food")
    store: Mapped[Store] = relationship("Store")
    unit: Mapped["Unit | None"] = relationship("Unit")

    @property
    def unit_cost(self) -> float:
        if self.unit_size == 0:
            return 0
        return self.price / self.unit_size

    def __repr__(self) -> str:
        return f"<FoodPrice {self.food_id} @ {self.store_id}: ${self.price}/{self.unit_size}>"
