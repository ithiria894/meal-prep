from __future__ import annotations

from datetime import date
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class WeeklySpecial(Base):
    __tablename__ = "weekly_specials"

    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[float | None] = mapped_column(Float)
    discount_pct: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[str | None] = mapped_column(String)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)

    food: Mapped["Food | None"] = relationship("Food")

    @property
    def savings(self) -> float | None:
        if self.original_price:
            return self.original_price - self.price
        return None

    def __repr__(self) -> str:
        return f"<WeeklySpecial {self.name} ${self.price} ({self.discount_pct}% off)>"
