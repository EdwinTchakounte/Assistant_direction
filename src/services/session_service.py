"""
Service sessions : gestion des conversations et de leur historique.

Ce service est la base de la MEMOIRE CONVERSATIONNELLE (10 pts au bareme) :
  - Chaque conversation a un session_id (UUID genere par le serveur
    si absent) qui persiste entre les appels /agent/chat.
  - Tous les messages (user, assistant, tool) sont stockes pour
    pouvoir reconstruire l'historique lors du prochain appel.

Le service reste HTTP-agnostique : il leve des exceptions metier
que les routes traduisent en HTTPException.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session as SQLASession

from src.models.db_models import Message, Session

logger = logging.getLogger(__name__)


# --- Exceptions metier ---------------------------------------
class SessionNotFoundError(Exception):
    """Leve quand une session demandee explicitement n'existe pas."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session id={session_id} introuvable.")
        self.session_id = session_id


# --- Operations principales ----------------------------------
def get_or_create_session(
    db: SQLASession,
    session_id: Optional[str] = None,
) -> Session:
    """
    Recupere une session existante ou en cree une nouvelle.

    Regles :
      - session_id absent/vide -> genere un UUID et cree la session
      - session_id existant    -> retourne la session
      - session_id inconnu     -> cree une nouvelle session avec cet id
                                  (permet au client de choisir son id)
    """
    # Cas 1 : id absent ou vide -> on en genere un nouveau
    if not session_id or not session_id.strip():
        new_id = str(uuid.uuid4())
        session = Session(id=new_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info("Nouvelle session creee (auto) : %s", new_id)
        return session

    # Cas 2 : id fourni -> on le cherche
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is not None:
        return session

    # Cas 3 : id fourni mais inconnu -> on le cree
    session = Session(id=session_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Nouvelle session creee (id client) : %s", session_id)
    return session


def require_session(db: SQLASession, session_id: str) -> Session:
    """
    Retourne la session ou leve SessionNotFoundError.
    Utilise par GET /session/{id}/history qui doit 404 si absente.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is None:
        raise SessionNotFoundError(session_id)
    return session


def append_message(
    db: SQLASession,
    session_id: str,
    role: str,
    content: str,
    tool_name: Optional[str] = None,
) -> Message:
    """
    Ajoute un message a l'historique d'une session.

    Parametres :
      role      : "user" | "assistant" | "tool"
      content   : texte du message (ou JSON d'un tool result)
      tool_name : nom du tool (seulement pour role=tool OU pour marquer
                  un tour assistant ou un tool a ete appele -> utile
                  pour remplir tool_used dans ChatResponse).
    """
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        tool_name=tool_name,
    )
    try:
        db.add(msg)
        db.commit()
        db.refresh(msg)
    except Exception:
        db.rollback()
        raise
    return msg


def get_messages(db: SQLASession, session_id: str) -> list[Message]:
    """
    Retourne l'historique complet d'une session, trie par timestamp.
    Ne leve pas d'erreur si la session n'a aucun message — retourne [].
    """
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp.asc(), Message.id.asc())
        .all()
    )


def count_user_turns(db: SQLASession, session_id: str) -> int:
    """
    Compte le nombre de messages utilisateur dans une session.
    Sert a calculer le champ `turn` de ChatResponse.
    """
    return (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.role == "user")
        .count()
    )
