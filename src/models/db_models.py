"""
Modeles SQLAlchemy : structure des tables en base.

3 tables :
  - events    : les rendez-vous de l'agenda (outil agenda)
  - sessions  : les conversations avec l'agent (memoire)
  - messages  : les echanges dans chaque session

Ne PAS confondre avec les schemas Pydantic (src/models/schemas.py)
qui definissent les structures d'entree/sortie de l'API.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

# Classe parente de tous les modeles ORM.
# Au demarrage, Base.metadata.create_all() cree toutes les tables declarees ici.
Base = declarative_base()


class Event(Base):
    """Un evenement de l'agenda (rendez-vous, reunion, etc.)."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    date = Column(String(10), nullable=False)          # format ISO YYYY-MM-DD
    time = Column(String(5), nullable=False)           # format HH:MM
    participants = Column(String(500), nullable=True)  # liste separee par virgules
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Session(Base):
    """Une conversation avec l'agent IA — contient N messages."""

    __tablename__ = "sessions"

    # id est un UUID genere cote serveur (voir session_service), stocke en string.
    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relation 1-N : session.messages renvoie la liste ordonnee des messages.
    # cascade="all, delete-orphan" : supprimer la session supprime ses messages.
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.timestamp",
    )


class Message(Base):
    """Un echange dans une session (user, assistant, ou resultat d'un tool)."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)

    # role : "user" | "assistant" | "tool"
    # On garde une string simple plutot qu'un Enum pour rester flexible
    # avec le format attendu par l'API Groq.
    role = Column(String(20), nullable=False)

    content = Column(Text, nullable=False)

    # tool_name : nom du tool appele (seulement pour les tours ou tool_used != null)
    # Servira a remplir le champ `tool_used` de la reponse /agent/chat.
    tool_name = Column(String(100), nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relation inverse vers Session
    session = relationship("Session", back_populates="messages")
