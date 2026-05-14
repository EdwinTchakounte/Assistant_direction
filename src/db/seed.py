"""
Seed des donnees initiales.

Deux jeux de donnees :
  - seed_users()  : 5 comptes demo (user1..user5 @ inov-consulting.com)
                    avec roles varies, pour permettre aux candidats frontend
                    de tester l'authentification et d'avoir plusieurs profils
                    a explorer. Idempotent.
  - seed_events() : 5 evenements d'agenda definis dans l'enonce, avec dates
                    calculees dynamiquement (J+1..J+4). Idempotent.

Idempotents : si la table contient deja des enregistrements, on n'insere rien.
"""
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session as SQLASession

from src.db.database import SessionLocal
from src.models.db_models import Event, User
from src.services import user_service

logger = logging.getLogger(__name__)


# =============================================================
# USERS — 5 comptes demo
# =============================================================
# Tous partagent le meme mot de passe (Innov2026!) pour simplifier
# le test frontend. Les roles et profils varient pour permettre au
# candidat de tester l'affichage de differents cas.

_DEMO_PASSWORD = "Innov2026!"

_DEMO_USERS: list[dict] = [
    {
        "email": "user1@inov-consulting.com",
        "full_name": "Jean Mbarga",
        "role": "director",
        "department": "Direction generale",
        "phone": "+237 6 90 11 11 11",
    },
    {
        "email": "user2@inov-consulting.com",
        "full_name": "Sophie Ndongo",
        "role": "manager",
        "department": "Operations",
        "phone": "+237 6 90 22 22 22",
    },
    {
        "email": "user3@inov-consulting.com",
        "full_name": "Paul Eyenga",
        "role": "manager",
        "department": "Finance",
        "phone": "+237 6 90 33 33 33",
    },
    {
        "email": "user4@inov-consulting.com",
        "full_name": "Marie Atangana",
        "role": "user",
        "department": "Ressources humaines",
        "phone": "+237 6 90 44 44 44",
    },
    {
        "email": "user5@inov-consulting.com",
        "full_name": "Pierre Fouda",
        "role": "user",
        "department": "Tech",
        "phone": "+237 6 90 55 55 55",
    },
]


def seed_users(db: SQLASession | None = None) -> int:
    """
    Cree les 5 comptes demo si la table users est vide.
    Retourne le nombre d'utilisateurs crees (0 si table deja peuplee).
    """
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        existing = db.query(User).count()
        if existing > 0:
            logger.info(
                "Seed users ignore : %d utilisateur(s) deja present(s).", existing
            )
            return 0

        for entry in _DEMO_USERS:
            user_service.create_user(
                db,
                email=entry["email"],
                password=_DEMO_PASSWORD,
                full_name=entry["full_name"],
                role=entry["role"],
                status="active",
                department=entry["department"],
                phone=entry["phone"],
            )

        logger.info("Seed users effectue : %d comptes crees.", len(_DEMO_USERS))
        return len(_DEMO_USERS)

    except Exception:
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()


# =============================================================
# EVENTS — agenda initial
# =============================================================

def _build_initial_events() -> list[Event]:
    """Construit la liste des 5 evenements initiaux avec dates dynamiques."""
    today = date.today()
    j1 = (today + timedelta(days=1)).isoformat()
    j2 = (today + timedelta(days=2)).isoformat()
    j3 = (today + timedelta(days=3)).isoformat()
    j4 = (today + timedelta(days=4)).isoformat()

    return [
        Event(
            title="Comite de direction",
            date=j1,
            time="09:00",
            participants="DG, DAF, DSI",
            notes="Budget Q2 a valider",
        ),
        Event(
            title="Reunion equipe Tech",
            date=j1,
            time="14:30",
            participants="Lead Dev, DevOps",
            notes="Point sprint en cours",
        ),
        Event(
            title="Call client Ministere",
            date=j2,
            time="11:00",
            participants="Client, Chef de projet",
            notes="Revue livrables phase 2",
        ),
        Event(
            title="Dejeuner partenaire",
            date=j3,
            time="12:30",
            participants="Partenaire externe",
            notes="Hotel Hilton Yaounde",
        ),
        Event(
            title="Revue RH mensuelle",
            date=j4,
            time="10:00",
            participants="DRH, Managers",
            notes="Evaluations semestrielles",
        ),
    ]


def seed_events(db: SQLASession | None = None) -> int:
    """
    Insere les 5 evenements initiaux SI la table events est vide.
    Retourne le nombre d'evenements inseres (0 si deja peuplee).
    """
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        existing = db.query(Event).count()
        if existing > 0:
            logger.info(
                "Seed events ignore : %d evenement(s) deja present(s).", existing
            )
            return 0

        events = _build_initial_events()
        db.add_all(events)
        db.commit()
        logger.info("Seed events effectue : %d evenement(s) inseres.", len(events))
        return len(events)

    except Exception:
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()
