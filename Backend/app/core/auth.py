"""
Authentification : hachage des mots de passe (bcrypt) et JWT.

- Aucun mot de passe en clair en base.
- JWT stocké uniquement en cookie HTTP-only (pas de localStorage).
- bcrypt utilisé directement (limite 72 octets : on tronque si besoin).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# bcrypt n'accepte pas plus de 72 octets
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Hache le mot de passe avec bcrypt. À utiliser à l'inscription."""
    password_bytes = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie que le mot de passe en clair correspond au hash stocké."""
    password_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Crée un JWT avec le subject (en général l'id utilisateur en string).
    Retourne le token (à mettre dans un cookie côté route).
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str | None:
    """
    Décode le JWT et retourne le subject (id user) ou None si invalide/expiré.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        return sub
    except JWTError:
        return None
