import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.budget import Expense, MonthlyBudget

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["budget"])


class BudgetCreate(BaseModel):
    year: int
    month: int
    budget_limit: float = 500.0


class ExpenseCreate(BaseModel):
    date: date
    amount: float
    category: str = "grocery"
    description: str | None = None
    store_id: int | None = None


class ExpenseRead(BaseModel):
    id: int
    date: date
    amount: float
    category: str
    description: str | None
    model_config = {"from_attributes": True}


class BudgetRead(BaseModel):
    id: int
    year: int
    month: int
    budget_limit: float
    total_spent: float
    remaining: float
    daily_allowance: float
    expenses: list[ExpenseRead] = []
    model_config = {"from_attributes": True}


@router.post("/budgets", response_model=BudgetRead)
def create_budget(data: BudgetCreate, session: Session = Depends(get_session)):
    existing = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == data.year, MonthlyBudget.month == data.month
    ).first()
    if existing:
        existing.budget_limit = data.budget_limit
        session.commit()
        session.refresh(existing)
        return existing

    budget = MonthlyBudget(year=data.year, month=data.month, budget_limit=data.budget_limit)
    session.add(budget)
    session.commit()
    session.refresh(budget)
    log.info("Created budget: %d-%02d $%.2f", data.year, data.month, data.budget_limit)
    return budget


@router.get("/budgets/current", response_model=BudgetRead)
def get_current_budget(session: Session = Depends(get_session)):
    today = date.today()
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == today.year, MonthlyBudget.month == today.month
    ).first()
    if not budget:
        budget = MonthlyBudget(year=today.year, month=today.month, budget_limit=500.0)
        session.add(budget)
        session.commit()
        session.refresh(budget)
    return budget


@router.post("/budgets/expenses", response_model=ExpenseRead)
def add_expense(data: ExpenseCreate, session: Session = Depends(get_session)):
    d = data.date
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == d.year, MonthlyBudget.month == d.month
    ).first()
    if not budget:
        budget = MonthlyBudget(year=d.year, month=d.month, budget_limit=500.0)
        session.add(budget)
        session.flush()

    expense = Expense(
        budget_id=budget.id,
        date=d,
        amount=data.amount,
        category=data.category,
        description=data.description,
        store_id=data.store_id,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)

    log.info("Expense: $%.2f %s (%s) — remaining $%.2f",
             data.amount, data.category, data.description, budget.remaining)

    if budget.remaining < 0:
        log.warning("OVER BUDGET! $%.2f over limit", abs(budget.remaining))

    return expense


@router.get("/budgets/{year}/{month}", response_model=BudgetRead)
def get_budget(year: int, month: int, session: Session = Depends(get_session)):
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == year, MonthlyBudget.month == month
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    return budget


@router.get("/budgets/summary")
def budget_summary(session: Session = Depends(get_session)):
    today = date.today()
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == today.year, MonthlyBudget.month == today.month
    ).first()
    if not budget:
        return {"message": "No budget set", "limit": 500, "spent": 0, "remaining": 500}

    by_category = {}
    for e in budget.expenses:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount

    return {
        "month": f"{today.year}-{today.month:02d}",
        "limit": budget.budget_limit,
        "spent": budget.total_spent,
        "remaining": budget.remaining,
        "daily_allowance": budget.daily_allowance,
        "by_category": by_category,
        "over_budget": budget.remaining < 0,
    }


@router.delete("/budgets/expenses/{expense_id}")
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(404, "Expense not found")
    session.delete(expense)
    session.commit()
    return {"deleted": expense_id}


@router.patch("/budgets/{year}/{month}")
def update_budget_limit(year: int, month: int, budget_limit: float, session: Session = Depends(get_session)):
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == year, MonthlyBudget.month == month
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    budget.budget_limit = budget_limit
    session.commit()
    return {"updated": f"{year}-{month:02d}", "new_limit": budget_limit}


@router.delete("/budgets/reset/{year}/{month}")
def reset_budget(year: int, month: int, session: Session = Depends(get_session)):
    budget = session.query(MonthlyBudget).filter(
        MonthlyBudget.year == year, MonthlyBudget.month == month
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    for e in budget.expenses:
        session.delete(e)
    session.commit()
    return {"reset": f"{year}-{month:02d}", "expenses_deleted": True}
