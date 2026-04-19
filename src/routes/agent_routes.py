"""
Route HTTP du point d'entree principal de l'agent : POST /agent/chat.

Delegue toute la logique (tool calling, memoire) a agent_service.
Le format de ChatResponse respecte strictement l'enonce :
  { session_id, response, tool_used, turn }
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as SQLASession

from src.db.database import get_db
from src.models.schemas import ChatRequest, ChatResponse
from src.services import agent_service

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
        "requete. Si aucun outil n'est necessaire, la valeur est null."
    ),
)
def chat(
    payload: ChatRequest,
    db: SQLASession = Depends(get_db),
) -> ChatResponse:
    return agent_service.chat(
        db=db,
        session_id=payload.session_id,
        user_message=payload.message,
    )
