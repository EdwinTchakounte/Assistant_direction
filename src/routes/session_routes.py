"""
Route HTTP pour consulter l'historique d'une session conversationnelle.

GET /session/{session_id}/history -> SessionHistoryResponse
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLASession

from src.db.database import get_db
from src.models.schemas import MessageResponse, SessionHistoryResponse
from src.services import session_service
from src.services.session_service import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["session"])


@router.get(
    "/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Recuperer l'historique complet d'une session",
    responses={404: {"description": "Session introuvable"}},
)
def get_history(
    session_id: str,
    db: SQLASession = Depends(get_db),
) -> SessionHistoryResponse:
    try:
        session_service.require_session(db, session_id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )

    messages = session_service.get_messages(db, session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )
