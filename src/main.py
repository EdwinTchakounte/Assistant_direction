"""
Point d'entree de l'application FastAPI.
Assistant de Direction — Inov Consulting.

Le `/` redirige vers `/docs` : aucune landing HTML, seulement la
documentation Swagger pour les candidats frontend.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session as SQLASession

from src.core.config import settings
from src.db.database import get_db, init_db
from src.db.seed import seed_events, seed_users
from src.routes import (
    agenda_routes,
    agent_routes,
    auth_routes,
    session_routes,
    user_routes,
)

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
      2. Seed du compte utilisateur demo (idempotent)
      3. Seed des 5 evenements initiaux (idempotent)

    A l'arret : rien a nettoyer ici (SQLAlchemy ferme ses connexions seul).
    """
    logger.info("Startup — initialisation de la base de donnees.")
    init_db()
    users_created = seed_users()
    events_created = seed_events()
    logger.info(
        "Startup termine (%d utilisateur(s), %d evenement(s) seedes).",
        users_created,
        events_created,
    )

    yield

    logger.info("Shutdown — arret propre.")


app = FastAPI(
    title="Assistant de Direction — Inov Consulting",
    description=(
        "API backend d'un agent IA capable de gerer un agenda "
        "et de synthetiser des documents via tool calling (Groq LLM).\n\n"
        "**Endpoints exposes au frontend du test technique :**\n"
        "- `POST /auth/login` — authentification\n"
        "- `GET /users/me` — profil utilisateur connecte\n"
        "- `POST /agent/chat` — interaction avec l'assistant IA"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# --- CORS : permet aux frontends d'appeler l'API depuis un autre domaine ---
# Wildcard "*" pratique en environnement de test, a restreindre en prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,  # incompatible avec allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(agent_routes.router)
app.include_router(agenda_routes.router)
app.include_router(session_routes.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirige la racine vers la documentation Swagger."""
    return RedirectResponse(url="/docs", status_code=307)


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
