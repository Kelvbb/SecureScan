"""Routes d'authentification : inscription, connexion, déconnexion. JWT en cookie HTTP-only."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.auth import create_access_token, hash_password, verify_password
from app.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse

router = APIRouter()


def _set_token_cookie(response: Response, token: str) -> None:
    """Enregistre le JWT dans un cookie HTTP-only (pas de localStorage)."""
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def _clear_token_cookie(response: Response) -> None:
    """Supprime le cookie JWT (déconnexion)."""
    response.delete_cookie(
        key=settings.JWT_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """Inscription : crée un utilisateur. Mot de passe haché (bcrypt), jamais stocké en clair."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email.",
        )
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
def login(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Connexion : vérifie email + mot de passe, pose un cookie HTTP-only contenant le JWT.
    Aucun token renvoyé dans le corps JSON (tout est dans le cookie).
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )
    token = create_access_token(subject=str(user.id))
    _set_token_cookie(response, token)
    return UserResponse.model_validate(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    """Déconnexion : supprime le cookie JWT."""
    _clear_token_cookie(response)
    return {"message": "Déconnexion réussie."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retourne l'utilisateur connecté (lu via le cookie JWT). 401 si non connecté."""
    return UserResponse.model_validate(current_user)
