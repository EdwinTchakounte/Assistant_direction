"""
Modeles SQLAlchemy : structure des tables en base.

4 tables :
  - users     : comptes utilisateurs (authentification)
  - events    : les rendez-vous de l'agenda (outil agenda)
  - sessions  : les conversations avec l'agent (memoire), liees a un user
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


class User(Base):
    """Compte utilisateur de l'application (authentification + profil)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profil affiche dans l'ecran "Informations utilisateur" du frontend.
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="user")  # director, manager, user...
    status = Column(String(20), nullable=False, default="active")  # active, inactive
    department = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relation 1-N : sessions de chat appartenant a ce user.
    sessions = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )


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
    """Une conversation avec l'agent IA — contient N messages, appartient a un user."""

    __tablename__ = "sessions"

    # id est un UUID genere cote serveur (voir session_service), stocke en string.
    id = Column(String(36), primary_key=True)

    # Une session est liee a son utilisateur proprietaire.
    # Nullable pour la retro-compatibilite avec d'eventuelles sessions anonymes
    # creees avant l'introduction de l'auth ; mais en pratique, toute session
    # creee via /agent/chat (authentifie) aura un user_id.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")

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
