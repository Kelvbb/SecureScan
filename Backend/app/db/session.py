"""Session SQLAlchemy et factory de connexion."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée les tables (en dev). En prod préférer les migrations."""
    # Imports tardifs pour éviter les importations circulaires
    from app.models import (  # noqa: F401
        OwaspCategory,
        Scan,
        ScanMetrics,
        SecurityTool,
        SuggestedFix,
        ToolExecution,
        User,
        Vulnerability,
    )
    Base.metadata.create_all(bind=engine)
