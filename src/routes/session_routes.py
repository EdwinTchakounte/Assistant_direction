"""
Route HTTP pour consulter l'historique d'une session conversationnelle.

GET /session/{session_id}/history -> SessionHistoryResponse

Authentification requise : seul le proprietaire de la session peut
consulter son historique.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLASession

from src.db.database import get_db
from src.models.db_models import User
from src.models.schemas import MessageResponse, SessionHistoryResponse
from src.services import session_service
from src.services.session_service import SessionForbiddenError, SessionNotFoundError
from src.services.user_service import get_current_user

router = APIRouter(prefix="/session", tags=["session"])


@router.get(
    "/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Recuperer l'historique complet d'une session",
    responses={
        401: {"description": "Token absent, invalide ou expire"},
        403: {"description": "Session appartenant a un autre utilisateur"},
        404: {"description": "Session introuvable"},
    },
)
def get_history(
    session_id: str,
    db: SQLASession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionHistoryResponse:
    try:
        session_service.require_session(db, session_id, user_id=current_user.id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )
    except SessionForbiddenError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )

    messages = session_service.get_messages(db, session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )
