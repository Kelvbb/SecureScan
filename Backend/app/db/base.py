"""Déclaration de la base pour les modèles SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base commune à tous les modèles."""

    pass
