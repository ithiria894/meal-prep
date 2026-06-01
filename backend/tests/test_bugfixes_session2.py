"""Regression tests for the two bugs found during Session 2 (2026-05-31).

Bug 1: MealPlanEntry was missing the `is_batch_cook` column, so POST /plans
       (and the model constructor) raised TypeError.
Bug 2: consume_fifo did not convert units, so "need 200 g" would eat a whole
       "1 pack" batch as if 1 == 200.
"""

import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
from app.models.food import Food, Unit
from app.models.stock import Location, StockEntry
from app.models.plan import MealPlan, MealPlanEntry
from app.services.stock_manager import stock_in, consume_fifo


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


# ---------------------------------------------------------------------------
# Bug 1 — is_batch_cook column exists and is constructible
# ---------------------------------------------------------------------------

def test_meal_plan_entry_accepts_is_batch_cook(session):
    """Constructing a MealPlanEntry with is_batch_cook must NOT raise."""
    plan = MealPlan(week_start_date=date(2026, 6, 1), name="week")
    session.add(plan)
    session.flush()

    entry = MealPlanEntry(
        meal_plan_id=plan.id,
        date=date(2026, 6, 1),
        meal_type="dinner",
        servings_wanted=4,
        is_batch_cook=True,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    assert entry.is_batch_cook is True


def test_meal_plan_entry_is_batch_cook_defaults_true(session):
    """Default value should be True (matches schema default)."""
    plan = MealPlan(week_start_date=date(2026, 6, 1))
    session.add(plan)
    session.flush()
    entry = MealPlanEntry(meal_plan_id=plan.id, date=date(2026, 6, 1))
    session.add(entry)
    session.commit()
    session.refresh(entry)
    assert entry.is_batch_cook is True


# ---------------------------------------------------------------------------
# Bug 2 — consume_fifo converts between units
# ---------------------------------------------------------------------------

@pytest.fixture
def unit_setup(session):
    u_g = Unit(name="g", abbreviation="g")
    u_kg = Unit(name="kg", abbreviation="kg")
    session.add_all([u_g, u_kg])
    session.flush()
    loc = Location(name="fridge", type="fridge")
    session.add(loc)
    session.flush()
    beef = Food(name="牛肉", default_unit_id=u_g.id)
    session.add(beef)
    session.flush()
    return {"g": u_g.id, "kg": u_kg.id, "loc": loc.id, "beef": beef.id}


def test_consume_converts_kg_stock_for_gram_request(session, unit_setup):
    """Stock stored as 1 kg, recipe asks for 200 g.

    Old bug: would treat 1 == 200, eat the whole batch, report deficit.
    Fixed: 200 g of a 1 kg (=1000 g) batch => 0.8 kg remaining.
    """
    stock_in(session, food_id=unit_setup["beef"], amount=1.0,
             location_id=unit_setup["loc"], unit_id=unit_setup["kg"])

    consumed = consume_fifo(session, food_id=unit_setup["beef"],
                            amount_needed=200.0, unit_id=unit_setup["g"])

    assert consumed == pytest.approx(200.0)  # consumed amount reported in grams

    entry = session.query(StockEntry).filter_by(food_id=unit_setup["beef"]).one()
    # 1 kg - 200 g = 0.8 kg left, batch NOT exhausted
    assert entry.amount == pytest.approx(0.8)
    assert entry.is_exhausted is False


def test_consume_same_unit_unchanged(session, unit_setup):
    """Same-unit consume still works exactly (no regression)."""
    stock_in(session, food_id=unit_setup["beef"], amount=500.0,
             location_id=unit_setup["loc"], unit_id=unit_setup["g"])

    consumed = consume_fifo(session, food_id=unit_setup["beef"],
                            amount_needed=200.0, unit_id=unit_setup["g"])

    assert consumed == pytest.approx(200.0)
    entry = session.query(StockEntry).filter_by(food_id=unit_setup["beef"]).one()
    assert entry.amount == pytest.approx(300.0)


def test_consume_exhausts_kg_batch_when_fully_used(session, unit_setup):
    """Consuming 1000 g from a 1 kg batch exhausts it exactly."""
    stock_in(session, food_id=unit_setup["beef"], amount=1.0,
             location_id=unit_setup["loc"], unit_id=unit_setup["kg"])

    consumed = consume_fifo(session, food_id=unit_setup["beef"],
                            amount_needed=1000.0, unit_id=unit_setup["g"])

    assert consumed == pytest.approx(1000.0)
    entry = session.query(StockEntry).filter_by(food_id=unit_setup["beef"]).one()
    assert entry.amount == pytest.approx(0.0)
    assert entry.is_exhausted is True
