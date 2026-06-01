from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


disliked_foods_table = Table(
    "user_disliked_foods",
    Base.metadata,
    Column("preference_id", Integer, ForeignKey("user_preferences.id"), primary_key=True),
    Column("food_id", Integer, ForeignKey("foods.id"), primary_key=True),
)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_name: Mapped[str] = mapped_column(String, nullable=False, default="default")
    meals_per_week: Mapped[int] = mapped_column(Integer, default=10)
    max_same_dish_per_week: Mapped[int] = mapped_column(Integer, default=3)
    cooking_skill_level: Mapped[str] = mapped_column(String, default="beginner")
    default_batch_cook_day: Mapped[str] = mapped_column(String, default="saturday")
    max_spice_level: Mapped[int] = mapped_column(Integer, default=1)

    disliked_foods: Mapped[list["Food"]] = relationship("Food", secondary=disliked_foods_table)
    dietary_tags: Mapped[list[DietaryTag]] = relationship(
        "DietaryTag", back_populates="preferences", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<UserPreferences {self.user_name}>"


class DietaryTag(Base):
    __tablename__ = "dietary_tags"

    preference_id: Mapped[int] = mapped_column(ForeignKey("user_preferences.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)

    preferences: Mapped[UserPreferences] = relationship("UserPreferences", back_populates="dietary_tags")

    def __repr__(self) -> str:
        return f"<DietaryTag {self.tag}>"
