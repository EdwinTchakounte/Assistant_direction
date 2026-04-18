"""
Service agenda : logique metier CRUD des evenements.

Les fonctions prennent la session DB en parametre (injection) pour
rester testables unitairement sans serveur HTTP.

Le service est volontairement HTTP-agnostique : il leve des
exceptions metier (EventNotFoundError) que la couche route
traduit en HTTPException.
"""
from datetime import date as date_cls, timedelta
from typing import Optional

from sqlalchemy.orm import Session as SQLASession

from src.models.db_models import Event
from src.models.schemas import EventCreate, EventUpdate


# --- Exceptions metier ---------------------------------------
class EventNotFoundError(Exception):
    """Leve quand un evenement demande par son id n'existe pas."""

    def __init__(self, event_id: int) -> None:
        super().__init__(f"Evenement id={event_id} introuvable.")
        self.event_id = event_id


# --- Operations CRUD -----------------------------------------
def list_events(
    db: SQLASession,
    date_filter: Optional[str] = None,
    range_filter: Optional[str] = None,
) -> list[Event]:
    """
    Liste les evenements, avec filtres optionnels.

    Priorite des filtres :
      1. date_filter ("YYYY-MM-DD") -> date exacte
      2. range_filter ("week")      -> aujourd'hui + 6 jours
      3. sinon                      -> tous les evenements

    Les resultats sont tries par date puis heure.
    """
    query = db.query(Event)

    if date_filter:
        query = query.filter(Event.date == date_filter)
    elif range_filter == "week":
        today = date_cls.today()
        end = today + timedelta(days=6)
        query = query.filter(
            Event.date >= today.isoformat(),
            Event.date <= end.isoformat(),
        )

    return query.order_by(Event.date.asc(), Event.time.asc()).all()


def get_event(db: SQLASession, event_id: int) -> Event:
    """Recupere un evenement par son id. Leve EventNotFoundError si absent."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise EventNotFoundError(event_id)
    return event


def create_event(db: SQLASession, payload: EventCreate) -> Event:
    """Cree un nouvel evenement et retourne l'objet avec son id genere."""
    event = Event(
        title=payload.title,
        date=payload.date,
        time=payload.time,
        participants=payload.participants,
        notes=payload.notes,
    )
    try:
        db.add(event)
        db.commit()
        db.refresh(event)  # recupere l'id et created_at generes par la DB
    except Exception:
        db.rollback()
        raise
    return event


def update_event(
    db: SQLASession, event_id: int, payload: EventUpdate
) -> Event:
    """
    Met a jour les champs fournis (non None) d'un evenement existant.
    Leve EventNotFoundError si l'evenement n'existe pas.
    """
    event = get_event(db, event_id)  # leve si absent

    # Recupere uniquement les champs explicitement fournis dans le payload
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(event, field, value)

    try:
        db.commit()
        db.refresh(event)
    except Exception:
        db.rollback()
        raise
    return event


def delete_event(db: SQLASession, event_id: int) -> None:
    """Supprime un evenement. Leve EventNotFoundError si absent."""
    event = get_event(db, event_id)  # leve si absent
    try:
        db.delete(event)
        db.commit()
    except Exception:
        db.rollback()
        raise
