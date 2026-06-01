import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.stock import FreezerPortion, Location, StockEntry
from app.schemas.stock import (
    ConsumeRequest, FreezerPortionRead,
    LocationCreate, LocationRead,
    QuickHaveRequest, StockEntryRead, StockInRequest,
)
from app.services.stock_manager import (
    consume_fifo, create_freezer_portions, get_expiring_soon, stock_in,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stock"])


@router.post("/locations", response_model=LocationRead)
def create_location(data: LocationCreate, session: Session = Depends(get_session)):
    loc = Location(name=data.name, type=data.type)
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


@router.get("/locations", response_model=list[LocationRead])
def list_locations(session: Session = Depends(get_session)):
    return session.query(Location).all()


@router.post("/stock", response_model=StockEntryRead)
def add_stock(data: StockInRequest, session: Session = Depends(get_session)):
    entry = stock_in(
        session,
        food_id=data.food_id,
        amount=data.amount,
        location_id=data.location_id,
        unit_id=data.unit_id,
        best_before_date=data.best_before_date,
        price=data.price,
        store_id=data.store_id,
    )
    return entry


@router.post("/stock/quick-have", response_model=StockEntryRead)
def quick_have(data: QuickHaveRequest, session: Session = Depends(get_session)):
    """Mark a food as 'I have this' without specifying amount/location/expiry."""
    existing = (
        session.query(StockEntry)
        .filter(StockEntry.food_id == data.food_id, StockEntry.is_quick_have == True, StockEntry.is_exhausted == False)  # noqa: E712
        .first()
    )
    if existing:
        log.info("Food %d already marked as quick-have", data.food_id)
        return existing
    entry = StockEntry(food_id=data.food_id, is_quick_have=True)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    log.info("Quick-have: food %d marked as available", data.food_id)
    return entry


@router.get("/stock", response_model=list[StockEntryRead])
def list_stock(include_exhausted: bool = False, session: Session = Depends(get_session)):
    q = session.query(StockEntry)
    if not include_exhausted:
        q = q.filter(StockEntry.is_exhausted == False)  # noqa: E712
    return q.order_by(StockEntry.best_before_date.asc().nullslast()).all()


@router.post("/stock/consume")
def consume_stock(data: ConsumeRequest, session: Session = Depends(get_session)):
    consumed = consume_fifo(
        session,
        food_id=data.food_id,
        amount_needed=data.amount,
        unit_id=data.unit_id,
        recipe_id=data.recipe_id,
    )
    return {"consumed": consumed, "requested": data.amount, "deficit": max(0, data.amount - consumed)}


@router.get("/stock/expiring", response_model=list[StockEntryRead])
def expiring_soon(days: int = 3, session: Session = Depends(get_session)):
    return get_expiring_soon(session, days)


@router.get("/freezer", response_model=list[FreezerPortionRead])
def list_freezer_portions(session: Session = Depends(get_session)):
    return (
        session.query(FreezerPortion)
        .filter(FreezerPortion.consumed_count < FreezerPortion.cube_count)
        .order_by(FreezerPortion.best_before_date.asc().nullslast())
        .all()
    )


@router.post("/freezer/{portion_id}/consume")
def consume_portion(portion_id: int, count: int = 1, session: Session = Depends(get_session)):
    portion = session.get(FreezerPortion, portion_id)
    if not portion:
        raise HTTPException(404, "Freezer portion not found")
    if portion.consumed_count + count > portion.cube_count:
        raise HTTPException(400, f"Only {portion.remaining} cubes remaining")
    portion.consumed_count += count
    session.commit()
    session.refresh(portion)
    log.info("Consumed %d cube(s) of %s (%d remaining)", count, portion.recipe_name, portion.remaining)
    return {"remaining": portion.remaining}


@router.patch("/stock/{entry_id}")
def update_stock(entry_id: int, amount: float | None = None, best_before_date: str | None = None, session: Session = Depends(get_session)):
    entry = session.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Stock entry not found")
    if amount is not None:
        entry.amount = amount
    if best_before_date:
        from datetime import date as d
        entry.best_before_date = d.fromisoformat(best_before_date)
    session.commit()
    return {"updated": entry_id}


@router.delete("/stock/{entry_id}")
def delete_stock(entry_id: int, session: Session = Depends(get_session)):
    entry = session.get(StockEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Stock entry not found")
    session.delete(entry)
    session.commit()
    return {"deleted": entry_id}
