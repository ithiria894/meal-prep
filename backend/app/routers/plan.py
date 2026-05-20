import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.plan import MealPlan, MealPlanEntry
from app.schemas.plan import MealPlanCreate, MealPlanRead

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["plan"])


@router.post("/plans", response_model=MealPlanRead)
def create_plan(data: MealPlanCreate, session: Session = Depends(get_session)):
    plan = MealPlan(week_start_date=data.week_start_date, name=data.name)
    session.add(plan)
    session.flush()

    for entry_data in data.entries:
        session.add(MealPlanEntry(
            meal_plan_id=plan.id,
            recipe_id=entry_data.recipe_id,
            servings_wanted=entry_data.servings_wanted,
            date=entry_data.date,
            meal_type=entry_data.meal_type,
            is_batch_cook=entry_data.is_batch_cook,
        ))

    session.commit()
    session.refresh(plan)
    log.info("Created meal plan: %s (%d entries)", plan.week_start_date, len(plan.entries))
    return plan


@router.get("/plans", response_model=list[MealPlanRead])
def list_plans(session: Session = Depends(get_session)):
    return session.query(MealPlan).order_by(MealPlan.week_start_date.desc()).all()


@router.get("/plans/{plan_id}", response_model=MealPlanRead)
def get_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(MealPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Meal plan not found")
    return plan


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, session: Session = Depends(get_session)):
    plan = session.get(MealPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Meal plan not found")
    session.delete(plan)
    session.commit()
    return {"deleted": plan_id}
