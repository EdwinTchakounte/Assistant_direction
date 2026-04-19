"""
Point d'entree de l'application FastAPI.
Assistant de Direction — Inov Consulting.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as SQLASession

from src.core.config import settings
from src.db.database import get_db, init_db
from src.db.seed import seed_events
from src.routes import agenda_routes, agent_routes, session_routes

# Logger module
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Hook de demarrage/arret de l'application.

    Au demarrage :
      1. Creation des tables si elles n'existent pas (init_db)
      2. Seed des 5 evenements initiaux (idempotent)

    A l'arret : rien a nettoyer ici (SQLAlchemy ferme ses connexions seul).
    """
    logger.info("Startup — initialisation de la base de donnees.")
    init_db()
    inserted = seed_events()
    logger.info("Startup termine (%d evenement(s) seedes).", inserted)

    yield

    logger.info("Shutdown — arret propre.")


app = FastAPI(
    title="Assistant de Direction — Inov Consulting",
    description=(
        "API backend d'un agent IA capable de gerer un agenda "
        "et de synthetiser des documents via tool calling (Groq LLM)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- Routers ---
app.include_router(agenda_routes.router)
app.include_router(agent_routes.router)
app.include_router(session_routes.router)


@app.get("/health", tags=["system"])
def health(db: SQLASession = Depends(get_db)) -> dict:
    """
    Statut de l'API et de la base de donnees.

    - 200 : API + DB operationnelles
    - 503 : DB injoignable (API up mais degradee)
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Health check : DB indisponible.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "down", "error": str(exc)},
        )

    return {
        "status": "ok",
        "service": "assistant-direction",
        "database": "connected",
    }
