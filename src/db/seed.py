"""
Seed des donnees initiales de l'agenda.

5 evenements definis dans l'enonce, avec dates calculees dynamiquement
a partir d'aujourd'hui (J+1, J+2, J+3, J+4) comme exige par le sujet.

Idempotent : si la table events contient deja des enregistrements,
on n'insere rien (pas de doublons au re-demarrage).
"""
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session as SQLASession

from src.db.database import SessionLocal
from src.models.db_models import Event

logger = logging.getLogger(__name__)


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

    Parametre `db` optionnel : si non fourni, une session est creee
    localement (pratique pour appel depuis le startup FastAPI).
    """
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        existing = db.query(Event).count()
        if existing > 0:
            logger.info(
                "Seed ignore : %d evenement(s) deja present(s) en base.", existing
            )
            return 0

        events = _build_initial_events()
        db.add_all(events)
        db.commit()
        logger.info("Seed effectue : %d evenement(s) inseres.", len(events))
        return len(events)

    except Exception:
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()
