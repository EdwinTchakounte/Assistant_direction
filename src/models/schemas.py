"""
Schemas Pydantic pour les entrees/sorties de l'API.

A ne PAS confondre avec db_models.py :
  - db_models.py  -> structure des tables en DB (SQLAlchemy)
  - schemas.py    -> structure des JSON echanges avec le client (Pydantic)

Cette separation permet :
  - de ne pas exposer toutes les colonnes DB au client
  - de valider les entrees au niveau HTTP avant d'atteindre la logique
  - de documenter automatiquement l'API via Swagger
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================
# AGENDA — Evenements
# =============================================================

class EventBase(BaseModel):
    """Champs communs a la creation et a la lecture d'un evenement."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Titre de l'evenement",
        examples=["Comite de direction"],
    )
    date: str = Field(
        ...,
        description="Date au format ISO YYYY-MM-DD",
        examples=["2026-04-18"],
    )
    time: str = Field(
        ...,
        description="Heure au format HH:MM (24h)",
        examples=["09:00"],
    )
    participants: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Liste de participants separes par des virgules",
        examples=["DG, DAF, DSI"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Notes libres",
        examples=["Budget Q2 a valider"],
    )

    @field_validator("date")
    @classmethod
    def _validate_date_format(cls, v: str) -> str:
        """Verifie que la date est au format YYYY-MM-DD et represente une date valide."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as err:
            raise ValueError("date doit etre au format YYYY-MM-DD") from err
        return v

    @field_validator("time")
    @classmethod
    def _validate_time_format(cls, v: str) -> str:
        """Verifie que l'heure est au format HH:MM (24h)."""
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as err:
            raise ValueError("time doit etre au format HH:MM") from err
        return v


class EventCreate(EventBase):
    """Payload de POST /agenda."""
    pass


class EventUpdate(BaseModel):
    """
    Payload de PATCH /agenda/{id} : tous les champs sont optionnels.
    Le service n'updatera que les champs fournis (non None).
    """
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    date: Optional[str] = None
    time: Optional[str] = None
    participants: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def _validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as err:
            raise ValueError("date doit etre au format YYYY-MM-DD") from err
        return v

    @field_validator("time")
    @classmethod
    def _validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as err:
            raise ValueError("time doit etre au format HH:MM") from err
        return v


class EventResponse(EventBase):
    """Evenement tel que renvoye par l'API (inclut id et created_at)."""

    id: int
    created_at: datetime

    # Permet a Pydantic d'accepter un objet SQLAlchemy en entree
    # (Event de db_models.py) et d'en extraire les attributs.
    model_config = ConfigDict(from_attributes=True)


# =============================================================
# AGENT — Chat
# =============================================================

class ChatRequest(BaseModel):
    """Payload de POST /agent/chat."""

    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Identifiant de session. Si null ou absent, le serveur "
            "en genere un nouveau."
        ),
        examples=[None, "7f3c1b0e-1a2b-4c5d-9e8f-0a1b2c3d4e5f"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Message utilisateur en langage naturel",
        examples=["Quels sont mes rendez-vous de demain ?"],
    )


class ChatResponse(BaseModel):
    """Reponse de POST /agent/chat."""

    session_id: str = Field(
        ..., description="Identifiant de session a reutiliser dans le prochain appel"
    )
    response: str = Field(..., description="Reponse en langage naturel de l'agent")
    tool_used: Optional[str] = Field(
        default=None,
        description=(
            "Nom du tool appele par l'agent (ex: get_agenda). "
            "null si aucun outil n'a ete active."
        ),
    )
    turn: int = Field(..., ge=1, description="Numero d'echange dans la session")


# =============================================================
# SESSIONS — Historique
# =============================================================

class MessageResponse(BaseModel):
    """Un message dans l'historique d'une session."""

    role: str = Field(..., description="user | assistant | tool")
    content: str
    tool_name: Optional[str] = Field(
        default=None, description="Nom du tool si role=tool ou si un tool a ete appele"
    )
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionHistoryResponse(BaseModel):
    """Historique complet d'une session."""

    session_id: str
    messages: list[MessageResponse]
