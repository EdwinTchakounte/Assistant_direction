"""
Routes HTTP pour la gestion de l'agenda.

Responsabilites :
  - Valider les entrees via Pydantic (automatique)
  - Appeler agenda_service pour la logique metier
  - Traduire les exceptions metier en HTTPException
  - Specifier les status codes et response_model pour Swagger

Note : les routes ne touchent PAS la DB directement, tout passe
par agenda_service.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as SQLASession

from src.db.database import get_db
from src.models.schemas import EventCreate, EventResponse, EventUpdate
from src.services import agenda_service
from src.services.agenda_service import EventNotFoundError

router = APIRouter(prefix="/agenda", tags=["agenda"])


# --- Helpers --------------------------------------------------
def _not_found(err: EventNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(err),
    )


# --- Endpoints ------------------------------------------------
@router.get(
    "",
    response_model=list[EventResponse],
    summary="Lister les evenements",
    description=(
        "Retourne la liste des evenements. Filtres optionnels :\n"
        "- `?date=YYYY-MM-DD` pour une date exacte\n"
        "- `?range=week` pour les 7 prochains jours\n"
        "Si les deux sont fournis, `date` est prioritaire."
    ),
)
def list_events(
    date: Optional[str] = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filtrer par date exacte (YYYY-MM-DD)",
        examples=["2026-04-18"],
    ),
    range: Optional[Literal["week"]] = Query(
        default=None,
        description="Filtrer par plage temporelle ('week' = 7 prochains jours)",
    ),
    db: SQLASession = Depends(get_db),
) -> list[EventResponse]:
    events = agenda_service.list_events(db, date_filter=date, range_filter=range)
    return [EventResponse.model_validate(e) for e in events]


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Creer un evenement",
)
def create_event(
    payload: EventCreate,
    db: SQLASession = Depends(get_db),
) -> EventResponse:
    event = agenda_service.create_event(db, payload)
    return EventResponse.model_validate(event)


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Recuperer un evenement par son id",
    responses={404: {"description": "Evenement introuvable"}},
)
def get_event(
    event_id: int,
    db: SQLASession = Depends(get_db),
) -> EventResponse:
    try:
        event = agenda_service.get_event(db, event_id)
    except EventNotFoundError as err:
        raise _not_found(err)
    return EventResponse.model_validate(event)


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    summary="Modifier un ou plusieurs champs d'un evenement",
    responses={404: {"description": "Evenement introuvable"}},
)
def update_event(
    event_id: int,
    payload: EventUpdate,
    db: SQLASession = Depends(get_db),
) -> EventResponse:
    try:
        event = agenda_service.update_event(db, event_id, payload)
    except EventNotFoundError as err:
        raise _not_found(err)
    return EventResponse.model_validate(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un evenement",
    responses={
        204: {"description": "Evenement supprime"},
        404: {"description": "Evenement introuvable"},
    },
)
def delete_event(
    event_id: int,
    db: SQLASession = Depends(get_db),
) -> None:
    try:
        agenda_service.delete_event(db, event_id)
    except EventNotFoundError as err:
        raise _not_found(err)
    # Pas de retour : 204 No Content
