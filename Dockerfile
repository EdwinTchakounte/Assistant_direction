# =============================================================
# Dockerfile — Assistant de Direction (FastAPI + Groq)
# =============================================================

# Image Python officielle, variante "slim" (~50 Mo) : suffisante
# pour un backend FastAPI, sans les lourdeurs d'une image full.
FROM python:3.11-slim

# Variables d'environnement pour un Python "container-friendly" :
# - PYTHONDONTWRITEBYTECODE : pas de .pyc sur disque (inutile en conteneur)
# - PYTHONUNBUFFERED : logs en temps reel (stdout non bufferise)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# --- Etape 1 : dependances (mise en cache) -------------------
# On copie UNIQUEMENT requirements.txt d'abord. Tant que ce fichier
# ne change pas, Docker reutilise la couche "pip install" :
# les rebuilds deviennent 10x plus rapides.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Etape 2 : code source -----------------------------------
# Copie apres l'install car il change beaucoup plus souvent.
COPY src/ ./src/

# Dossier pour la base SQLite (monte en volume en compose)
RUN mkdir -p /app/data

# Port expose (doit matcher API_PORT dans .env)
EXPOSE 8000

# Commande de lancement : uvicorn sert l'app FastAPI.
# --host 0.0.0.0 est OBLIGATOIRE en conteneur (sinon inaccessible).
# $PORT est injecte par Render/Railway/Fly ; fallback 8000 en local.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
