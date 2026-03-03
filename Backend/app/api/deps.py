"""Dépendances injectables : DB et authentification (JWT lu depuis le cookie)."""

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Lit le JWT depuis le cookie (pas le header). Retourne l'utilisateur ou 401.
    À utiliser sur les routes protégées.
    """
    token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Non authentifié.")
    user_id_str = decode_access_token(token)
    if not user_id_str:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token invalide ou expiré.")
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token invalide.")
    user = db.get(User, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """
    Même chose que get_current_user mais retourne None au lieu de 401 si pas de cookie.
    Utile pour des routes qui s'adaptent (ex. /me qui doit quand même 401 si pas connecté,
    donc on utilise get_current_user pour /me en fait).
    """
    token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if not token:
        return None
    user_id_str = decode_access_token(token)
    if not user_id_str:
        return None
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None
    return db.get(User, user_id)
