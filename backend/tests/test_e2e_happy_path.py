"""E2E test for v2 model with BatchCookPlan and staple skipping."""

import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import Base
from app.models.food import Food, Unit
from app.models.recipe import Recipe, RecipeIngredient
from app.models.stock import Location, StockEntry
from app.models.plan import MealPlan, MealPlanEntry, BatchCookPlan, BatchCookEntry
from app.models.shopping import ShoppingList, ShoppingListItem, ShoppingListItemSource
from app.models.store import Store
from app.models.user_preferences import UserPreferences
from app.services.shopping_aggregator import generate_shopping_list
from app.services.stock_manager import stock_in, consume_fifo


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture
def setup(session):
    # Units
    u_pcs = Unit(name="隻", abbreviation="pcs")
    u_bowl = Unit(name="碗")
    u_g = Unit(name="g", abbreviation="g")
    u_piece = Unit(name="個")
    u_tbsp = Unit(name="湯匙", abbreviation="tbsp")
    u_can = Unit(name="罐")
    session.add_all([u_pcs, u_bowl, u_g, u_piece, u_tbsp, u_can])
    session.flush()

    # Foods
    egg = Food(name="蛋", default_unit_id=u_pcs.id)
    tomato = Food(name="番茄", default_unit_id=u_piece.id, default_shelf_life_days=7)
    beef = Food(name="牛肉", default_unit_id=u_g.id)
    canned_tom = Food(name="罐頭番茄", default_unit_id=u_can.id)
    pasta = Food(name="意粉", default_unit_id=u_g.id, is_staple=True)
    macaroni = Food(name="通粉", default_unit_id=u_g.id, is_staple=True)
    oil = Food(name="油", default_unit_id=u_tbsp.id, is_staple=True)
    tom_paste = Food(name="番茄醬", default_unit_id=u_tbsp.id, is_staple=True)
    salt = Food(name="鹽", is_staple=True)
    session.add_all([egg, tomato, beef, canned_tom, pasta, macaroni, oil, tom_paste, salt])
    session.flush()

    # Locations
    fridge = Location(name="雪櫃", type="fridge")
    pantry = Location(name="廚房", type="pantry")
    session.add_all([fridge, pantry])
    session.flush()

    # Recipes
    bolognese = Recipe(name="肉醬意粉", servings=2, type="main",
                       freeze_method="souper_cube", freeze_shelf_life_days=14)
    session.add(bolognese)
    session.flush()
    session.add_all([
        RecipeIngredient(recipe_id=bolognese.id, food_id=pasta.id, unit_id=u_g.id,
                         quantity=200, original_text="意粉 200g"),
        RecipeIngredient(recipe_id=bolognese.id, food_id=beef.id, unit_id=u_g.id,
                         quantity=200, original_text="牛肉碎 200g"),
        RecipeIngredient(recipe_id=bolognese.id, food_id=canned_tom.id, unit_id=u_can.id,
                         quantity=1, original_text="罐頭番茄 1罐"),
        RecipeIngredient(recipe_id=bolognese.id, food_id=tom_paste.id, unit_id=u_tbsp.id,
                         quantity=2, original_text="番茄醬 2湯匙"),
    ])

    tom_egg = Recipe(name="番茄炒蛋", servings=2, type="main",
                     freeze_method="souper_cube", freeze_shelf_life_days=7)
    session.add(tom_egg)
    session.flush()
    session.add_all([
        RecipeIngredient(recipe_id=tom_egg.id, food_id=egg.id, unit_id=u_pcs.id,
                         quantity=3, original_text="蛋 3隻"),
        RecipeIngredient(recipe_id=tom_egg.id, food_id=tomato.id, unit_id=u_piece.id,
                         quantity=2, original_text="番茄 2個"),
        RecipeIngredient(recipe_id=tom_egg.id, food_id=oil.id, unit_id=u_tbsp.id,
                         quantity=1, original_text="油 1湯匙"),
    ])

    tom_mac = Recipe(name="蕃茄通粉", servings=2, type="main",
                     freeze_method="souper_cube", freeze_shelf_life_days=7)
    session.add(tom_mac)
    session.flush()
    session.add_all([
        RecipeIngredient(recipe_id=tom_mac.id, food_id=macaroni.id, unit_id=u_g.id,
                         quantity=200, original_text="通粉 200g"),
        RecipeIngredient(recipe_id=tom_mac.id, food_id=tomato.id, unit_id=u_piece.id,
                         quantity=2, original_text="番茄 2個"),
        RecipeIngredient(recipe_id=tom_mac.id, food_id=egg.id, unit_id=u_pcs.id,
                         quantity=1, original_text="蛋 1隻"),
    ])

    session.commit()
    return {
        "egg": egg, "tomato": tomato, "beef": beef, "canned_tom": canned_tom,
        "pasta": pasta, "macaroni": macaroni, "oil": oil, "tom_paste": tom_paste,
        "bolognese": bolognese, "tom_egg": tom_egg, "tom_mac": tom_mac,
        "fridge": fridge, "pantry": pantry,
        "u_pcs": u_pcs, "u_g": u_g, "u_piece": u_piece, "u_can": u_can,
    }


def test_batch_cook_shopping_list_skips_staples(session, setup):
    """Batch cook plan: 肉醬意粉×6 + 番茄炒蛋×4 + 蕃茄通粉×4.
    Staples (意粉, 通粉, 油, 番茄醬) should be auto-skipped.
    Eggs in fridge should be deducted."""
    s = setup

    # Stock: 12 eggs in fridge
    stock_in(session, s["egg"].id, 12, s["fridge"].id, s["u_pcs"].id,
             best_before_date=date(2026, 6, 2))

    # Create plan with batch cook
    plan = MealPlan(week_start_date=date(2026, 5, 19), name="Test Week v2")
    session.add(plan)
    session.flush()

    bcp = BatchCookPlan(meal_plan_id=plan.id, date=date(2026, 5, 24))
    session.add(bcp)
    session.flush()

    session.add_all([
        BatchCookEntry(batch_cook_plan_id=bcp.id, recipe_id=s["bolognese"].id,
                       total_servings=6, eat_now_servings=2, freeze_servings=4),
        BatchCookEntry(batch_cook_plan_id=bcp.id, recipe_id=s["tom_egg"].id,
                       total_servings=4, eat_now_servings=2, freeze_servings=2),
        BatchCookEntry(batch_cook_plan_id=bcp.id, recipe_id=s["tom_mac"].id,
                       total_servings=4, eat_now_servings=2, freeze_servings=2),
    ])
    session.commit()

    sl = generate_shopping_list(session, plan.id)
    items = {session.get(Food, item.food_id).name: item for item in sl.items}

    # Staples should NOT appear
    assert "意粉" not in items
    assert "通粉" not in items
    assert "油" not in items
    assert "番茄醬" not in items

    # 蛋: 番茄炒蛋(4/2×3=6) + 蕃茄通粉(4/2×1=2) = 8 need, 12 have → 0 buy
    assert "蛋" not in items

    # 牛肉: 肉醬意粉(6/2×200=600g) need, 0 have → 600 buy
    assert items["牛肉"].quantity == pytest.approx(600.0)

    # 番茄: 番茄炒蛋(4/2×2=4) + 蕃茄通粉(4/2×2=4) = 8 need
    assert items["番茄"].quantity == pytest.approx(8.0)

    # 罐頭番茄: 肉醬意粉(6/2×1=3) need
    assert items["罐頭番茄"].quantity == pytest.approx(3.0)


def test_fifo_consume(session, setup):
    s = setup
    stock_in(session, s["egg"].id, 3, s["fridge"].id, s["u_pcs"].id,
             best_before_date=date(2026, 5, 20))
    stock_in(session, s["egg"].id, 3, s["fridge"].id, s["u_pcs"].id,
             best_before_date=date(2026, 5, 25))

    consumed = consume_fifo(session, s["egg"].id, 5, s["u_pcs"].id)
    assert consumed == pytest.approx(5.0)

    entries = (
        session.query(StockEntry)
        .filter(StockEntry.food_id == s["egg"].id)
        .order_by(StockEntry.best_before_date.asc())
        .all()
    )
    assert entries[0].is_exhausted is True
    assert entries[1].amount == pytest.approx(1.0)


def test_stock_deficit(session, setup):
    s = setup
    stock_in(session, s["egg"].id, 2, s["fridge"].id, s["u_pcs"].id)
    consumed = consume_fifo(session, s["egg"].id, 5, s["u_pcs"].id)
    assert consumed == pytest.approx(2.0)

    from app.models.stock import StockLog
    deficit = session.query(StockLog).filter(
        StockLog.food_id == s["egg"].id,
        StockLog.transaction_type == "deficit"
    ).first()
    assert deficit is not None
    assert deficit.amount == pytest.approx(3.0)
