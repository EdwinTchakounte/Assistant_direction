"""
Route HTTP du point d'entree principal de l'agent : POST /agent/chat.

Authentification requise : un JWT valide doit etre fourni dans le header
`Authorization: Bearer <token>` (obtenu via POST /auth/login).

Delegue toute la logique (tool calling, memoire) a agent_service.
Le format de ChatResponse respecte strictement l'enonce :
  { session_id, response, tool_used, turn }
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLASession

from src.db.database import get_db
from src.models.db_models import User
from src.models.schemas import ChatRequest, ChatResponse
from src.services import agent_service
from src.services.session_service import SessionForbiddenError
from src.services.user_service import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Discuter avec l'agent IA",
    description=(
        "Envoie un message a l'agent. Le `session_id` est genere par le "
        "serveur si absent ou vide, puis doit etre renvoye pour les tours "
        "suivants afin de conserver la memoire conversationnelle.\n\n"
        "Le champ `tool_used` indique si l'agent a active un outil "
        "(get_agenda, create_event, summarize_document) pour traiter la "
        "requete. Si aucun outil n'est necessaire, la valeur est null.\n\n"
        "**Authentification requise** : header `Authorization: Bearer <token>` "
        "obtenu via POST /auth/login. Chaque session de chat est isolee par utilisateur."
    ),
    responses={
        401: {"description": "Token absent, invalide ou expire"},
        403: {"description": "Session appartenant a un autre utilisateur"},
    },
)
def chat(
    payload: ChatRequest,
    db: SQLASession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    try:
        return agent_service.chat(
            db=db,
            session_id=payload.session_id,
            user_message=payload.message,
            user_id=current_user.id,
        )
    except SessionForbiddenError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        )
