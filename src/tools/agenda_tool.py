"""
Tools LLM pour la gestion de l'agenda.

Ces fonctions sont invoquees par l'agent via tool calling.
Elles wrappent agenda_service avec :
  - des signatures plates (types simples) pour le LLM
  - des sorties en JSON string (format attendu par Groq)
  - une gestion d'erreur qui renvoie une explication comprehensible
    par le LLM (qui la relaiera a l'utilisateur final)
"""
import json
import logging
from typing import Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session as SQLASession

from src.models.schemas import EventCreate
from src.services import agenda_service
from src.services.agenda_service import EventNotFoundError

logger = logging.getLogger(__name__)


def _event_to_dict(event) -> dict:
    """Convertit un objet Event (ORM) en dict serialisable."""
    return {
        "id": event.id,
        "title": event.title,
        "date": event.date,
        "time": event.time,
        "participants": event.participants,
        "notes": event.notes,
    }


def tool_get_agenda(
    db: SQLASession,
    date: Optional[str] = None,
    range: Optional[str] = None,  # noqa: A002 — shadow builtin volontaire
) -> str:
    """
    Tool LLM : recupere les evenements de l'agenda.

    Parametres :
      date  : str optionnel, format YYYY-MM-DD (date exacte)
      range : str optionnel, valeur "week" pour les 7 prochains jours

    Retourne un JSON string :
      {"count": N, "events": [{...}, ...]}
    """
    logger.info("Tool call: get_agenda(date=%s, range=%s)", date, range)

    events = agenda_service.list_events(db, date_filter=date, range_filter=range)
    payload = {
        "count": len(events),
        "events": [_event_to_dict(e) for e in events],
    }
    return json.dumps(payload, ensure_ascii=False)


def tool_create_event(
    db: SQLASession,
    title: str,
    date: str,
    time: str,
    participants: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Tool LLM : cree un nouvel evenement dans l'agenda.

    Parametres :
      title        : str, titre de l'evenement
      date         : str, format YYYY-MM-DD
      time         : str, format HH:MM
      participants : str optionnel, liste separee par des virgules
      notes        : str optionnel

    Retourne un JSON string :
      succes -> {"success": true, "event": {...}}
      erreur -> {"success": false, "error": "message"}
    """
    logger.info("Tool call: create_event(title=%s, date=%s, time=%s)", title, date, time)

    try:
        payload = EventCreate(
            title=title,
            date=date,
            time=time,
            participants=participants,
            notes=notes,
        )
    except ValidationError as err:
        # Format d'erreur comprehensible par le LLM
        errors = [f"{e['loc'][0]}: {e['msg']}" for e in err.errors()]
        return json.dumps(
            {"success": False, "error": "Donnees invalides: " + "; ".join(errors)},
            ensure_ascii=False,
        )

    event = agenda_service.create_event(db, payload)
    return json.dumps(
        {"success": True, "event": _event_to_dict(event)},
        ensure_ascii=False,
    )
