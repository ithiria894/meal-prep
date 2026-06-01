"""Stock management with FIFO consume and expiry tracking.

Based on Grocy's stock batch model.
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from app.models.food import Food, Unit
from app.models.stock import FreezerPortion, Location, StockEntry, StockLog
from app.services.unit_converter import convert

log = logging.getLogger(__name__)


def _unit_name(session: Session, unit_id: int | None) -> str | None:
    """Resolve a unit_id to its canonical name (for the conversion graph)."""
    if unit_id is None:
        return None
    unit = session.get(Unit, unit_id)
    if unit is None:
        return None
    # prefer abbreviation (g/kg/ml…) since the conversion graph keys on those
    return unit.abbreviation or unit.name


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
    cooked_at: datetime | None = None,
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

    # `amount_needed` is expressed in `unit_id`. Each stock batch may be stored
    # in a different unit, so we track the running shortfall in the REQUESTED
    # unit, and convert each batch's available amount into that unit before
    # taking from it. This stops the old bug where "need 200 g" silently ate a
    # whole "1 pack" batch as if 1 == 200.
    needed_unit = _unit_name(session, unit_id)

    remaining = amount_needed  # in requested unit
    consumed = 0.0  # in requested unit

    for entry in entries:
        if remaining <= 0:
            break

        entry_unit = _unit_name(session, entry.unit_id)
        # How much this batch holds, expressed in the requested unit.
        if needed_unit and entry_unit and entry_unit != needed_unit:
            avail_in_needed = convert(entry.amount, entry_unit, needed_unit)
            if avail_in_needed is None:
                # No conversion path — skip this batch rather than corrupt counts.
                log.warning(
                    "  FIFO skip batch=%s: cannot convert %s → %s",
                    entry.batch_id, entry_unit, needed_unit,
                )
                continue
        else:
            avail_in_needed = entry.amount

        if avail_in_needed <= 0:
            continue

        take_in_needed = min(avail_in_needed, remaining)
        # Convert the taken amount back to the batch's own unit to deduct it.
        ratio = take_in_needed / avail_in_needed  # fraction of this batch used
        take_in_entry = entry.amount * ratio

        entry.amount -= take_in_entry
        remaining -= take_in_needed
        consumed += take_in_needed

        if entry.amount <= 1e-9:
            entry.amount = 0.0
            entry.is_exhausted = True

        log.info("  FIFO consume: batch=%s, took=%.3f %s (=%.3f %s), remaining_in_batch=%.3f",
                 entry.batch_id, take_in_needed, needed_unit or "?",
                 take_in_entry, entry_unit or "?", entry.amount)

    log_entry = StockLog(
        food_id=food_id,
        amount=consumed,
        unit_id=unit_id,
        transaction_type="consume",
        related_recipe_id=recipe_id,
    )
    if cooked_at is not None:
        log_entry.created_at = cooked_at
    session.add(log_entry)

    if remaining > 0:
        deficit_log = StockLog(
            food_id=food_id,
            amount=remaining,
            unit_id=unit_id,
            transaction_type="deficit",
            related_recipe_id=recipe_id,
        )
        if cooked_at is not None:
            deficit_log.created_at = cooked_at
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
