from __future__ import annotations

from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str | None] = mapped_column(String)

    entries: Mapped[list[MealPlanEntry]] = relationship(
        "MealPlanEntry", back_populates="meal_plan", cascade="all, delete-orphan",
    )
    batch_cook_plan: Mapped[BatchCookPlan | None] = relationship(
        "BatchCookPlan", back_populates="meal_plan", uselist=False, cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MealPlan {self.week_start_date}>"


class MealPlanEntry(Base):
    __tablename__ = "meal_plan_entries"

    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String, nullable=False, default="dinner")

    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"))
    freezer_portion_id: Mapped[int | None] = mapped_column(ForeignKey("freezer_portions.id"))
    is_eating_out: Mapped[bool] = mapped_column(Boolean, default=False)
    is_batch_cook: Mapped[bool] = mapped_column(Boolean, default=True)
    servings_wanted: Mapped[int | None] = mapped_column(Integer)

    meal_plan: Mapped[MealPlan] = relationship("MealPlan", back_populates="entries")
    recipe: Mapped["Recipe | None"] = relationship("Recipe")
    freezer_portion: Mapped["FreezerPortion | None"] = relationship("FreezerPortion")

    def __repr__(self) -> str:
        if self.is_eating_out:
            return f"<MealPlanEntry {self.date} {self.meal_type} EATING OUT>"
        return f"<MealPlanEntry {self.date} {self.meal_type} recipe={self.recipe_id}>"


class BatchCookPlan(Base):
    __tablename__ = "batch_cook_plans"

    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    meal_plan: Mapped[MealPlan] = relationship("MealPlan", back_populates="batch_cook_plan")
    entries: Mapped[list[BatchCookEntry]] = relationship(
        "BatchCookEntry", back_populates="batch_cook_plan", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BatchCookPlan {self.date} ({len(self.entries)} entries)>"


class BatchCookEntry(Base):
    __tablename__ = "batch_cook_entries"

    batch_cook_plan_id: Mapped[int] = mapped_column(ForeignKey("batch_cook_plans.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    total_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    eat_now_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    freeze_servings: Mapped[int] = mapped_column(Integer, nullable=False)

    batch_cook_plan: Mapped[BatchCookPlan] = relationship("BatchCookPlan", back_populates="entries")
    recipe: Mapped["Recipe"] = relationship("Recipe")

    def __repr__(self) -> str:
        return f"<BatchCookEntry {self.recipe_id} total={self.total_servings} eat={self.eat_now_servings} freeze={self.freeze_servings}>"
