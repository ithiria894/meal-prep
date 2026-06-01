"""Tests for MODEL_V3 features (2026-05-31).

1. Food.preferred_store + is_shelf_stable
2. StockEntry.is_quick_have (quick-have marks)
3. shopping_aggregator skips quick-have foods
4. FoodSubstitution model
5. Recipe.spice_level + UserPreferences.max_spice_level
"""

import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
from app.models.food import Food, FoodSubstitution, Unit
from app.models.recipe import Recipe, RecipeIngredient
from app.models.stock import Location, StockEntry
from app.models.store import Store
from app.models.plan import MealPlan, MealPlanEntry
from app.models.user_preferences import UserPreferences
from app.services.shopping_aggregator import generate_shopping_list


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


# ---------------------------------------------------------------------------
# Feature 1: Food.preferred_store + is_shelf_stable
# ---------------------------------------------------------------------------

def test_food_preferred_store(session):
    store = Store(name="T&T")
    session.add(store)
    session.flush()

    food = Food(
        name="蒜蓉",
        preferred_store_id=store.id,
        store_reason="亞洲嘢 T&T 齊",
        is_shelf_stable=True,
    )
    session.add(food)
    session.commit()
    session.refresh(food)

    assert food.preferred_store.name == "T&T"
    assert food.store_reason == "亞洲嘢 T&T 齊"
    assert food.is_shelf_stable is True


def test_food_shelf_stable_defaults_false(session):
    food = Food(name="娃娃菜")
    session.add(food)
    session.commit()
    session.refresh(food)
    assert food.is_shelf_stable is False


# ---------------------------------------------------------------------------
# Feature 2: quick-have
# ---------------------------------------------------------------------------

def test_stock_entry_quick_have(session):
    food = Food(name="粉絲")
    session.add(food)
    session.flush()

    entry = StockEntry(food_id=food.id, is_quick_have=True)
    session.add(entry)
    session.commit()
    session.refresh(entry)

    assert entry.is_quick_have is True
    assert entry.amount == 0.0
    assert entry.location_id is None


# ---------------------------------------------------------------------------
# Feature 3: shopping_aggregator skips quick-have foods
# ---------------------------------------------------------------------------

def test_shopping_list_skips_quick_have_food(session):
    u = Unit(name="g", abbreviation="g")
    session.add(u)
    session.flush()
    loc = Location(name="pantry", type="pantry")
    session.add(loc)
    session.flush()

    garlic = Food(name="蒜蓉", default_unit_id=u.id)
    chili = Food(name="小米辣", default_unit_id=u.id)
    session.add_all([garlic, chili])
    session.flush()

    recipe = Recipe(name="蒜蓉粉絲娃娃菜", servings=1)
    session.add(recipe)
    session.flush()
    session.add(RecipeIngredient(recipe_id=recipe.id, food_id=garlic.id, unit_id=u.id, quantity=20.0, position=0))
    session.add(RecipeIngredient(recipe_id=recipe.id, food_id=chili.id, unit_id=u.id, quantity=5.0, position=1))
    session.flush()

    # Mark garlic as quick-have ("我有蒜蓉")
    session.add(StockEntry(food_id=garlic.id, is_quick_have=True))
    session.flush()

    plan = MealPlan(week_start_date=date(2026, 6, 2), name="test week")
    session.add(plan)
    session.flush()
    session.add(MealPlanEntry(meal_plan_id=plan.id, date=date(2026, 6, 2), recipe_id=recipe.id, servings_wanted=1))
    session.commit()

    sl = generate_shopping_list(session, plan.id)

    food_ids = [item.food_id for item in sl.items]
    assert garlic.id not in food_ids, "garlic (quick-have) should be skipped"
    assert chili.id in food_ids, "chili should be on the list"


# ---------------------------------------------------------------------------
# Feature 4: FoodSubstitution
# ---------------------------------------------------------------------------

def test_food_substitution(session):
    garlic = Food(name="蒜蓉")
    xo = Food(name="XO醬")
    session.add_all([garlic, xo])
    session.flush()

    sub = FoodSubstitution(
        food_id=garlic.id,
        substitute_food_id=xo.id,
        ratio=0.5,
        note="XO醬已含蒜+蝦米+辣",
    )
    session.add(sub)
    session.commit()
    session.refresh(sub)

    assert sub.food.name == "蒜蓉"
    assert sub.substitute.name == "XO醬"
    assert sub.ratio == 0.5
    assert "蝦米" in sub.note


# ---------------------------------------------------------------------------
# Feature 5: spice_level
# ---------------------------------------------------------------------------

def test_recipe_spice_level(session):
    recipe = Recipe(name="XO醬炒飯", servings=1, spice_level=2)
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    assert recipe.spice_level == 2


def test_recipe_spice_level_defaults_zero(session):
    recipe = Recipe(name="臘腸飯", servings=1)
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    assert recipe.spice_level == 0


def test_user_max_spice_level(session):
    prefs = UserPreferences(max_spice_level=1)
    session.add(prefs)
    session.commit()
    session.refresh(prefs)
    assert prefs.max_spice_level == 1
