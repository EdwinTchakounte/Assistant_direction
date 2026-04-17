"""
Connexion a la base de donnees et helpers SQLAlchemy.

Fournit :
  - engine       : connexion bas-niveau
  - SessionLocal : factory de sessions SQLAlchemy (transactions)
  - get_db()     : dependance FastAPI (1 db par requete HTTP)
  - init_db()    : cree les tables au demarrage

Note terminologique :
  "Session SQLAlchemy" (ici) = contexte de transaction DB.
  "Session conversationnelle" (table sessions) = echange user/agent.
  Pour eviter la confusion, on appelle toujours la premiere `db` dans le code.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLASession, sessionmaker

from src.core.config import settings
from src.models.db_models import Base


# --- Engine : la connexion SQLite -----------------------------
# check_same_thread=False : necessaire car FastAPI utilise plusieurs
# threads ; chaque requete a sa propre session donc c'est sur.
# Uniquement pertinent pour SQLite — ignore pour PostgreSQL.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,  # passer a True pour logger toutes les requetes SQL (debug)
)


# --- Factory de sessions SQLAlchemy ---------------------------
# autoflush=False : on decide quand flush (plus de controle).
# autocommit=False : il faut commit() explicitement (securite).
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=SQLASession,
)


# --- Dependance FastAPI ---------------------------------------
def get_db() -> Generator[SQLASession, None, None]:
    """
    Fournit une session DB a une route FastAPI.

    Usage :
        @router.get("/...")
        def route(db: Session = Depends(get_db)):
            db.query(...)

    Le yield garantit que la session est fermee meme en cas d'erreur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Initialisation : creation des tables ---------------------
def init_db() -> None:
    """
    Cree toutes les tables definies dans db_models.py si elles n'existent pas.
    Appele au demarrage de l'app (startup event).
    """
    Base.metadata.create_all(bind=engine)
