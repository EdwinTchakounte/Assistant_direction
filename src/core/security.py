"""
Helpers de securite : hash de mot de passe et signature JWT.

Isole les details cryptographiques (bcrypt, JWT) du reste du code pour
que les services restent lisibles et que la techno soit remplacable.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

# Contexte passlib configure pour bcrypt.
# bcrypt est le standard pour le hash de mots de passe : lent par design
# (resistant au bruteforce) et integre un salt par hash.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Mots de passe ---------------------------------------------
def hash_password(plain_password: str) -> str:
    """Retourne le hash bcrypt d'un mot de passe en clair."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifie qu'un mot de passe en clair correspond a un hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# --- JWT --------------------------------------------------------
class TokenDecodeError(Exception):
    """Levee quand un JWT est invalide, expire ou mal forme."""


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Cree un JWT signé HS256.

    Parametres :
      subject      : identifiant principal place dans `sub` (id utilisateur)
      extra_claims : claims additionnels (ex: role, email) pour eviter un
                     aller-retour DB sur chaque requete si besoin

    Le token contient :
      - sub : identifiant du user
      - exp : timestamp d'expiration
      - iat : timestamp d'emission
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode et valide un JWT. Leve TokenDecodeError si invalide/expire.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as err:
        raise TokenDecodeError(str(err)) from err
