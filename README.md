# Assistant de Direction — Inov Consulting

> Backend FastAPI d'un agent IA (LLM Groq + tool calling) pour la gestion d'agenda et la synthèse de documents.

## 🚧 État actuel

Étape 2 — Initialisation. Le projet expose une route `/health`.

## Lancement rapide (Docker)

```bash
cp .env.example .env
# Éditer .env et renseigner GROQ_API_KEY
docker compose up --build
```

L'API sera disponible sur http://localhost:8000
- `GET /health` → statut
- `GET /docs` → Swagger

(Les autres endpoints seront ajoutés aux étapes suivantes.)
