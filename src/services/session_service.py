"""
Service sessions : gestion des conversations et de leur historique.

Ce service est la base de la MEMOIRE CONVERSATIONNELLE :
  - Chaque conversation a un session_id (UUID genere par le serveur
    si absent) qui persiste entre les appels /agent/chat.
  - Tous les messages (user, assistant, tool) sont stockes pour
    pouvoir reconstruire l'historique lors du prochain appel.
  - Chaque session est liee a un utilisateur proprietaire : un user
    ne peut ni lire ni continuer la session d'un autre.

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
    """Levee quand une session demandee explicitement n'existe pas."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session id={session_id} introuvable.")
        self.session_id = session_id


class SessionForbiddenError(Exception):
    """Levee quand un user tente d'acceder a une session qui ne lui appartient pas."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session id={session_id} non autorisee pour cet utilisateur.")
        self.session_id = session_id


# --- Operations principales ----------------------------------
def get_or_create_session(
    db: SQLASession,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[int] = None,
) -> Session:
    """
    Recupere une session existante ou en cree une nouvelle.

    Regles :
      - session_id absent/vide      -> genere un UUID et cree la session
      - session_id existant + user  -> retourne la session SI elle appartient
                                       a ce user, sinon SessionForbiddenError
      - session_id inconnu          -> cree une nouvelle session avec cet id
                                       (permet au client de choisir son id)

    Le user_id, si fourni, est associe a toute session creee et utilise pour
    valider l'acces a une session existante.
    """
    # Cas 1 : id absent ou vide -> on en genere un nouveau
    if not session_id or not session_id.strip():
        new_id = str(uuid.uuid4())
        session = Session(id=new_id, user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info("Nouvelle session creee (auto) : %s (user=%s)", new_id, user_id)
        return session

    # Cas 2 : id fourni -> on le cherche
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is not None:
        # Verifie l'appartenance : un user ne peut pas reprendre la session d'un autre.
        if user_id is not None and session.user_id is not None and session.user_id != user_id:
            raise SessionForbiddenError(session_id)

        # Cas legacy : session sans owner -> on l'adopte pour le user courant.
        if user_id is not None and session.user_id is None:
            session.user_id = user_id
            db.commit()
            db.refresh(session)

        return session

    # Cas 3 : id fourni mais inconnu -> on le cree
    session = Session(id=session_id, user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(
        "Nouvelle session creee (id client) : %s (user=%s)", session_id, user_id
    )
    return session


def require_session(
    db: SQLASession,
    session_id: str,
    *,
    user_id: Optional[int] = None,
) -> Session:
    """
    Retourne la session ou leve SessionNotFoundError.
    Si user_id est fourni, verifie egalement l'appartenance (SessionForbiddenError).
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if session is None:
        raise SessionNotFoundError(session_id)

    if user_id is not None and session.user_id is not None and session.user_id != user_id:
        raise SessionForbiddenError(session_id)

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
