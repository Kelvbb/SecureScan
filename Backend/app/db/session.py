"""Session SQLAlchemy et factory de connexion."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base

# Import des modèles pour que create_all les connaisse
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
    Base.metadata.create_all(bind=engine)
