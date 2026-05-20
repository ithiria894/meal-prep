"""Stock management with FIFO consume and expiry tracking.

Based on Grocy's stock batch model.
"""

import logging
import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.stock import FreezerPortion, Location, StockEntry, StockLog

log = logging.getLogger(__name__)


def stock_in(
    session: Session,
    food_id: int,
    amount: float,
    location_id: int,
    unit_id: int | None = None,
    best_before_date: date | None = None,
    price: float | None = None,
    store_id: int | None = None,
) -> StockEntry:
    food = session.get(Food, food_id)
    if not food:
        raise ValueError(f"Food {food_id} not found")

    if best_before_date is None and food.default_shelf_life_days:
        best_before_date = date.today() + timedelta(days=food.default_shelf_life_days)

    batch_id = str(uuid.uuid4())[:8]

    entry = StockEntry(
        food_id=food_id,
        location_id=location_id,
        amount=amount,
        unit_id=unit_id,
        best_before_date=best_before_date,
        purchased_date=date.today(),
        price=price,
        store_id=store_id,
        batch_id=batch_id,
    )
    session.add(entry)

    log_entry = StockLog(
        food_id=food_id,
        amount=amount,
        unit_id=unit_id,
        transaction_type="purchase",
        batch_id=batch_id,
    )
    session.add(log_entry)
    session.commit()

    log.info("Stocked in: %s ×%.1f (batch=%s, expires=%s)",
             food.name, amount, batch_id, best_before_date)
    return entry


def consume_fifo(
    session: Session,
    food_id: int,
    amount_needed: float,
    unit_id: int | None = None,
    recipe_id: int | None = None,
) -> float:
    entries = (
        session.query(StockEntry)
        .filter(
            StockEntry.food_id == food_id,
            StockEntry.is_exhausted == False,  # noqa: E712
        )
        .order_by(StockEntry.best_before_date.asc().nullslast())
        .all()
    )

    remaining = amount_needed
    consumed = 0.0

    for entry in entries:
        if remaining <= 0:
            break

        # TODO: unit conversion if entry.unit_id != unit_id
        take = min(entry.amount, remaining)
        entry.amount -= take
        remaining -= take
        consumed += take

        if entry.amount <= 0:
            entry.is_exhausted = True

        log.info("  FIFO consume: batch=%s, took=%.1f, remaining_in_batch=%.1f",
                 entry.batch_id, take, entry.amount)

    log_entry = StockLog(
        food_id=food_id,
        amount=consumed,
        unit_id=unit_id,
        transaction_type="consume",
        related_recipe_id=recipe_id,
    )
    session.add(log_entry)

    if remaining > 0:
        deficit_log = StockLog(
            food_id=food_id,
            amount=remaining,
            unit_id=unit_id,
            transaction_type="deficit",
            related_recipe_id=recipe_id,
        )
        session.add(deficit_log)
        log.warning("Stock deficit: food=%d, short by %.1f", food_id, remaining)

    session.commit()
    return consumed


def get_expiring_soon(session: Session, days: int = 3) -> list[StockEntry]:
    cutoff = date.today() + timedelta(days=days)
    return (
        session.query(StockEntry)
        .filter(
            StockEntry.is_exhausted == False,  # noqa: E712
            StockEntry.best_before_date != None,  # noqa: E711
            StockEntry.best_before_date <= cutoff,
        )
        .order_by(StockEntry.best_before_date.asc())
        .all()
    )


def create_freezer_portions(
    session: Session,
    recipe_id: int,
    recipe_name: str,
    cube_count: int,
    freezer_shelf_life_days: int = 14,
    location_id: int | None = None,
    total_cost: float | None = None,
) -> FreezerPortion:
    portion = FreezerPortion(
        recipe_id=recipe_id,
        recipe_name=recipe_name,
        cube_count=cube_count,
        date_prepared=date.today(),
        best_before_date=date.today() + timedelta(days=freezer_shelf_life_days),
        location_id=location_id,
        cost_per_cube=total_cost / cube_count if total_cost and cube_count > 0 else None,
    )
    session.add(portion)
    session.commit()

    log.info("Created %d freezer portions of %s (expires %s)",
             cube_count, recipe_name, portion.best_before_date)
    return portion
