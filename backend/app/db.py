import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models.base import Base

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "meal_prep.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    import app.models  # noqa: F401 — ensure all models are registered
    Base.metadata.create_all(engine)
    log.info("Database initialized at %s", DB_PATH)


def get_session() -> Session:
    return SessionLocal()
