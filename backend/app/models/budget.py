from __future__ import annotations

from datetime import date
from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MonthlyBudget(Base):
    __tablename__ = "monthly_budgets"

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_limit: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)

    expenses: Mapped[list[Expense]] = relationship(
        "Expense", back_populates="budget", cascade="all, delete-orphan",
    )

    @property
    def total_spent(self) -> float:
        return sum(e.amount for e in self.expenses)

    @property
    def remaining(self) -> float:
        return self.budget_limit - self.total_spent

    @property
    def daily_allowance(self) -> float:
        import calendar
        days_in_month = calendar.monthrange(self.year, self.month)[1]
        today = date.today()
        if today.year == self.year and today.month == self.month:
            days_left = days_in_month - today.day + 1
        else:
            days_left = days_in_month
        return self.remaining / max(days_left, 1)

    def __repr__(self) -> str:
        return f"<Budget {self.year}-{self.month:02d} ${self.budget_limit} (spent ${self.total_spent:.2f})>"


class Expense(Base):
    __tablename__ = "expenses"

    budget_id: Mapped[int] = mapped_column(ForeignKey("monthly_budgets.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="grocery")
    description: Mapped[str | None] = mapped_column(String)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))

    budget: Mapped[MonthlyBudget] = relationship("MonthlyBudget", back_populates="expenses")

    def __repr__(self) -> str:
        return f"<Expense {self.date} ${self.amount} {self.category}>"
