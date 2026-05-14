"""
Service utilisateurs : authentification + dependance FastAPI get_current_user.

Couvre :
  - creation d'un user (hash du mot de passe automatique)
  - lookup par email / id
  - authentification (verifie email + mot de passe)
  - extraction du user courant depuis le JWT (Bearer token)
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as SQLASession

from src.core.security import (
    TokenDecodeError,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.db.database import get_db
from src.models.db_models import User

logger = logging.getLogger(__name__)


# --- Exceptions metier ---------------------------------------
class UserNotFoundError(Exception):
    """Levee quand un user demande explicitement n'existe pas."""


class InvalidCredentialsError(Exception):
    """Levee quand email/mot de passe ne correspondent pas."""


class InactiveUserError(Exception):
    """Levee quand on tente d'authentifier un user inactif."""


# --- Operations CRUD -----------------------------------------
def get_by_email(db: SQLASession, email: str) -> Optional[User]:
    """Retourne le user correspondant a un email, ou None."""
    return db.query(User).filter(User.email == email.lower()).first()


def get_by_id(db: SQLASession, user_id: int) -> Optional[User]:
    """Retourne le user correspondant a un id, ou None."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: SQLASession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str = "user",
    status: str = "active",
    department: Optional[str] = None,
    phone: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> User:
    """
    Cree un nouvel utilisateur. Le mot de passe est hashé avant insertion.
    Email normalisé en minuscules pour eviter les doublons casse-differents.
    """
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        status=status,
        department=department,
        phone=phone,
        avatar_url=avatar_url,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


def authenticate(db: SQLASession, email: str, password: str) -> User:
    """
    Verifie un couple (email, mot de passe).

    Leve :
      - InvalidCredentialsError si l'email est inconnu OU le password est faux
        (on ne distingue PAS les deux cas pour ne pas leaker l'existence d'un compte)
      - InactiveUserError si le compte existe mais est inactif
    """
    user = get_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Email ou mot de passe invalide.")

    if user.status != "active":
        raise InactiveUserError(f"Compte {email} desactive.")

    return user


# --- Dependance FastAPI : user authentifie -------------------
_bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="JWT obtenu via POST /auth/login",
    auto_error=False,
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: SQLASession = Depends(get_db),
) -> User:
    """
    Dependance FastAPI : extrait le user courant depuis le header
    `Authorization: Bearer <token>` et le retourne.

    Leve HTTP 401 si :
      - header absent
      - token invalide / expire
      - user inconnu en DB
      - user desactive
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenDecodeError as err:
        logger.info("JWT invalide : %s", err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mal forme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mal forme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte desactive.",
        )

    return user
