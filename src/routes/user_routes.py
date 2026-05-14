"""
Routes utilisateur : GET /users/me.

Endpoint demande par le frontend pour afficher l'ecran "Informations utilisateur".
"""
from fastapi import APIRouter, Depends

from src.models.db_models import User
from src.models.schemas import UserResponse
from src.services.user_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil de l'utilisateur connecte",
    description=(
        "Retourne les informations du compte authentifie : "
        "nom complet, email, role, statut, departement, telephone, date de creation.\n\n"
        "Requiert un JWT valide dans le header `Authorization: Bearer <token>`."
    ),
    responses={
        401: {"description": "Token absent, invalide ou expire"},
        403: {"description": "Compte desactive"},
    },
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
