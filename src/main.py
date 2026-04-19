"""
Point d'entree de l'application FastAPI.
Assistant de Direction — Inov Consulting.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
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


_LANDING_HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Assistant de Direction — Inov Consulting</title>
<style>
  :root{
    --bg:#fafaf9;
    --surface:#ffffff;
    --ink:#1c1917;
    --ink-soft:#57534e;
    --mute:#a8a29e;
    --line:#e7e5e4;
    --line-soft:#f5f5f4;
    --acc:#4f46e5;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);color:var(--ink);line-height:1.6;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:820px;margin:0 auto;padding:72px 28px 96px}
  .eyebrow{
    color:var(--ink-soft);font-size:12px;letter-spacing:.12em;text-transform:uppercase;
    font-weight:500;margin-bottom:18px;
  }
  h1{font-size:32px;line-height:1.2;margin:0 0 14px;font-weight:600;letter-spacing:-.02em}
  .lead{color:var(--ink-soft);font-size:16px;margin:0 0 28px;max-width:640px}
  h2{
    font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--mute);
    font-weight:500;margin:48px 0 16px;
  }
  .actions{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
  .btn{
    display:inline-flex;align-items:center;gap:6px;
    padding:9px 16px;border-radius:8px;font-size:14px;font-weight:500;
    text-decoration:none;border:1px solid transparent;transition:all .15s;
  }
  .btn-primary{background:var(--ink);color:#fff}
  .btn-primary:hover{background:#000}
  .btn-ghost{background:var(--surface);color:var(--ink);border-color:var(--line)}
  .btn-ghost:hover{background:var(--line-soft)}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
  .card{
    background:var(--surface);border:1px solid var(--line);border-radius:10px;
    padding:18px 20px;transition:border-color .15s;
  }
  .card:hover{border-color:#d6d3d1}
  .card h3{margin:0 0 6px;font-size:14px;font-weight:600;color:var(--ink)}
  .card p{margin:0;color:var(--ink-soft);font-size:13.5px;line-height:1.55}
  .tags{display:flex;flex-wrap:wrap;gap:6px}
  .tag{
    display:inline-block;background:var(--surface);color:var(--ink-soft);
    border:1px solid var(--line);padding:4px 10px;border-radius:999px;font-size:12px;
  }
  .eps{
    background:var(--surface);border:1px solid var(--line);border-radius:10px;
    overflow:hidden;
  }
  .eps a.row{
    display:flex;align-items:center;gap:14px;padding:12px 18px;
    text-decoration:none;color:inherit;border-bottom:1px solid var(--line-soft);
    transition:background .12s;
  }
  .eps a.row:last-child{border-bottom:0}
  .eps a.row:hover{background:var(--line-soft)}
  .verb{
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
    font-size:10.5px;font-weight:600;letter-spacing:.04em;
    padding:3px 8px;border-radius:5px;min-width:56px;text-align:center;
  }
  .verb-get{background:#ecfdf5;color:#047857}
  .verb-post{background:#eef2ff;color:#4338ca}
  .verb-patch{background:#fffbeb;color:#b45309}
  .verb-delete{background:#fef2f2;color:#b91c1c}
  .eps code{color:var(--ink);font-size:13px}
  .eps .desc{color:var(--ink-soft);font-size:13px;margin-left:auto;text-align:right}
  code{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:13px}
  pre{
    background:var(--surface);border:1px solid var(--line);border-radius:10px;
    padding:16px 18px;overflow:auto;font-size:12.5px;color:var(--ink);margin:0;
  }
  a{color:var(--acc);text-decoration:none}
  a:hover{text-decoration:underline}
  footer{
    margin-top:56px;padding-top:20px;border-top:1px solid var(--line);
    color:var(--mute);font-size:12.5px;display:flex;justify-content:space-between;
  }
  @media(max-width:520px){
    .wrap{padding:48px 20px 72px}
    h1{font-size:26px}
    .eps .desc{display:none}
  }
</style>
</head>
<body>
  <div class="wrap">
    <div class="eyebrow">Inov Consulting &middot; Test technique</div>
    <h1>Assistant de Direction</h1>
    <p class="lead">
      Backend FastAPI d'un agent IA capable de gerer un agenda et de synthetiser des
      documents via tool calling (Groq LLM), avec memoire conversationnelle de session.
    </p>

    <div class="actions">
      <a class="btn btn-primary" href="https://assistant-direction-1.onrender.com/docs">Documentation Swagger</a>
      <a class="btn btn-ghost" href="https://assistant-direction-1.onrender.com/health">Health</a>
      <a class="btn btn-ghost" href="https://github.com/EdwinTchakounte/Assistant_direction">GitHub</a>
    </div>

    <h2>Fonctionnalites</h2>
    <div class="grid">
      <div class="card">
        <h3>Gestion d'agenda</h3>
        <p>L'agent lit, cree, modifie et supprime des evenements en langage naturel. CRUD complet.</p>
      </div>
      <div class="card">
        <h3>Synthese de document</h3>
        <p>Synthese structuree a partir d'un texte brut : points cles, decisions, actions.</p>
      </div>
      <div class="card">
        <h3>Memoire de session</h3>
        <p>Contexte conversationnel sur 5+ echanges. <code>session_id</code> genere par le serveur.</p>
      </div>
    </div>

    <h2>Stack</h2>
    <div class="tags">
      <span class="tag">Python 3.11</span>
      <span class="tag">FastAPI</span>
      <span class="tag">SQLAlchemy</span>
      <span class="tag">SQLite</span>
      <span class="tag">Pydantic v2</span>
      <span class="tag">Groq &middot; Llama 3.3 70B</span>
      <span class="tag">Pytest</span>
      <span class="tag">Docker</span>
    </div>

    <h2>Endpoints</h2>
    <div class="eps">
      <a class="row" href="https://assistant-direction-1.onrender.com/docs">
        <span class="verb verb-post">POST</span>
        <code>/agent/chat</code>
        <span class="desc">Point d'entree de l'agent</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/agenda">
        <span class="verb verb-get">GET</span>
        <code>/agenda</code>
        <span class="desc">Lister les evenements</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/docs">
        <span class="verb verb-post">POST</span>
        <code>/agenda</code>
        <span class="desc">Creer un evenement</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/docs">
        <span class="verb verb-patch">PATCH</span>
        <code>/agenda/{id}</code>
        <span class="desc">Modifier un evenement</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/docs">
        <span class="verb verb-delete">DELETE</span>
        <code>/agenda/{id}</code>
        <span class="desc">Supprimer un evenement</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/docs">
        <span class="verb verb-get">GET</span>
        <code>/session/{id}/history</code>
        <span class="desc">Historique de session</span>
      </a>
      <a class="row" href="https://assistant-direction-1.onrender.com/health">
        <span class="verb verb-get">GET</span>
        <code>/health</code>
        <span class="desc">Statut API + DB</span>
      </a>
    </div>

    <h2>Exemple</h2>
<pre><code>curl -X POST https://assistant-direction-1.onrender.com/agent/chat \\
  -H "Content-Type: application/json" \\
  -d '{"session_id": null, "message": "Quels sont mes rendez-vous de demain ?"}'</code></pre>

    <footer>
      <span>Assistant de Direction &middot; v0.1.0</span>
      <span>Inov Consulting</span>
    </footer>
  </div>
</body>
</html>"""


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def landing() -> HTMLResponse:
    """Page d'accueil presentant le projet et les endpoints."""
    return HTMLResponse(content=_LANDING_HTML, status_code=200)


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
