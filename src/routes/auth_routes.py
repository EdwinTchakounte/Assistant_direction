"""
Routes d'authentification : POST /auth/login.

Endpoint principal attendu par le frontend du test technique :
echange (email, password) contre un JWT et le profil utilisateur.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLASession

from src.core.config import settings
from src.core.security import create_access_token
from src.db.database import get_db
from src.models.schemas import LoginRequest, TokenResponse, UserResponse
from src.services import user_service
from src.services.user_service import InactiveUserError, InvalidCredentialsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authentification utilisateur",
    description=(
        "Echange un couple (email, password) contre un JWT a placer dans "
        "le header `Authorization: Bearer <token>` des requetes suivantes.\n\n"
        "**Compte demo (seedé au demarrage si la table users est vide) :**\n"
        "- email : `directeur@inov.com`\n"
        "- password : `Inov2026!`"
    ),
    responses={
        401: {"description": "Email ou mot de passe invalide"},
        403: {"description": "Compte desactive"},
    },
)
def login(
    payload: LoginRequest,
    db: SQLASession = Depends(get_db),
) -> TokenResponse:
    try:
        user = user_service.authenticate(db, payload.email, payload.password)
    except InvalidCredentialsError:
        # Reponse volontairement generique pour ne pas leaker l'existence d'un compte.
        logger.info("Login refuse pour %s (credentials invalides).", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserError:
        logger.info("Login refuse pour %s (compte inactif).", payload.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte desactive.",
        )

    token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )
