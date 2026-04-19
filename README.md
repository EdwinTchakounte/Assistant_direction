# Assistant de Direction — Inov Consulting

Backend FastAPI d'un agent IA doté de **tool calling réel** (via Groq) pour :
- Gérer l'agenda d'un directeur (consultation, création de rendez-vous)
- Synthétiser des documents professionnels (points clés, décisions, actions)
- Maintenir une **mémoire conversationnelle** sur plusieurs échanges

---

##  Stack technique (et pourquoi)

| Composant | Choix | Justification |
|---|---|---|
| **Backend** | Python 3.11 + FastAPI | Swagger auto-généré, validation Pydantic native, async natif, typage strict |
| **LLM** | Groq API (`llama-3.3-70b-versatile`) | Tier gratuit, tool calling natif, latence faible |
| **Intégration LLM** | SDK `groq` officiel (direct, sans LangChain) | Contrôle total de la boucle tool calling, transparence pour audit |
| **DB** | SQLite + SQLAlchemy 2.x | Zéro setup, suffisant pour ce test, modèle portable vers PostgreSQL |
| **Validation** | Pydantic v2 | Validation I/O + Settings (`.env`) + schémas Swagger auto |
| **Tests** | Pytest | Standard Python, fixtures pour DB en mémoire |
| **Conteneurisation** | Docker + docker-compose | Reproductibilité, lancement en 1 commande |

### Pourquoi SDK direct et pas LangChain ?

LangChain masque la boucle de tool calling derrière `AgentExecutor`. Le SDK Groq direct nous oblige à implémenter la boucle nous-mêmes → **transparence totale** sur comment le LLM décide, comment on exécute les tools, comment on re-alimente le contexte. Pour un test évaluant la **maîtrise** du tool calling, ce choix est assumé.

---

## Lancement 

### Prérequis
- Docker + Docker Compose v2 installés
- Une clé API Groq 

### Étape 1 — Récupérer le projet
```bash
git clone <url-du-depot>
cd assistant-direction
```

### Étape 2 — Configurer `.env`
```bash
cp .env.example .env
```
Ouvrir `.env` et renseigner `GROQ_API_KEY=gsk_...`. Le port par défaut est 8000 ; en cas de conflit, changer `API_PORT=8001`.

### Étape 3 — Lancer
```bash
docker compose up --build
```

L'API est disponible sur `http://localhost:${API_PORT}` (défaut 8000).
- Documentation Swagger interactive : http://localhost:8000/docs
- OpenAPI JSON brut : http://localhost:8000/openapi.json

### Vérification rapide
```bash
curl http://localhost:8000/health
# {"status":"ok","service":"assistant-direction","database":"connected"}
```

---

##  Lancer les tests

```bash
docker compose exec api pytest tests/ -v
```

12 tests unitaires couvrent le service agenda (CRUD, filtres, 404).

---

##  Endpoints principaux

### `POST /agent/chat` — point d'entrée principal

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "message": "Quels sont mes rendez-vous de demain ?"
  }'
```

Réponse :
```json
{
  "session_id": "7f3c1b0e-1a2b-4c5d-9e8f-0a1b2c3d4e5f",
  "response": "Vous avez deux rendez-vous demain : Comité de direction à 9h00 et Réunion équipe Tech à 14h30.",
  "tool_used": "get_agenda",
  "turn": 1
}
```

### Conserver le contexte (mémoire)

Réutiliser le `session_id` dans les appels suivants :
```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "7f3c1b0e-1a2b-4c5d-9e8f-0a1b2c3d4e5f",
    "message": "Et après-demain ?"
  }'
```

### Planifier un événement via l'agent

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "message": "Planifie une réunion vendredi 24 avril 2026 à 10h avec Lead Dev. Titre: Revue architecture."
  }'
# tool_used: "create_event"
```

### Synthétiser un document

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": null,
    "message": "Résume ce compte-rendu : Réunion du 15 avril, décision de geler les embauches..."
  }'
# tool_used: "summarize_document"
```

### Consulter l'historique d'une session
```bash
curl http://localhost:8000/session/7f3c1b0e.../history
```

### CRUD agenda direct (sans passer par l'agent)

```bash
# Lister tous les événements
curl http://localhost:8000/agenda

# Filtrer par date
curl "http://localhost:8000/agenda?date=2026-04-18"

# Filtrer la semaine
curl "http://localhost:8000/agenda?range=week"

# Créer
curl -X POST http://localhost:8000/agenda \
  -H "Content-Type: application/json" \
  -d '{"title":"RDV","date":"2026-04-25","time":"15:00"}'

# Modifier partiellement
curl -X PATCH http://localhost:8000/agenda/1 \
  -H "Content-Type: application/json" \
  -d '{"time":"10:30"}'

# Supprimer
curl -X DELETE http://localhost:8000/agenda/1
```

---

##  Architecture

```
src/
├── main.py                     # FastAPI app + lifespan (init_db, seed)
├── core/
│   ├── config.py               # Settings Pydantic (charge .env)
│   └── groq_client.py          # Singleton client Groq
├── models/
│   ├── db_models.py            # SQLAlchemy : Event, Session, Message
│   └── schemas.py              # Pydantic : I/O API + validators date/heure
├── db/
│   ├── database.py             # engine + get_db + init_db
│   └── seed.py                 # 5 événements initiaux (dates dynamiques J+1..J+4)
├── services/                   # Logique métier, HTTP-agnostique
│   ├── agenda_service.py       # CRUD + filtres + exceptions métier
│   ├── session_service.py      # Sessions + messages + turns
│   └── agent_service.py        # Boucle tool calling + mémoire
├── tools/                      # Tools exposés au LLM
│   ├── agenda_tool.py          # get_agenda, create_event (wrappers du service)
│   ├── summarize_tool.py       # summarize_document (appelle Groq)
│   └── registry.py             # TOOL_DEFINITIONS (JSON Schema) + dispatcher
└── routes/                     # Endpoints HTTP
    ├── agenda_routes.py        # /agenda (CRUD)
    ├── agent_routes.py         # /agent/chat
    └── session_routes.py       # /session/{id}/history

tests/
├── conftest.py                 # Fixture DB SQLite en mémoire
└── test_agenda_service.py      # 12 tests unitaires
```

### Séparation en couches

```
Client HTTP → routes → services → db_models / tools
                           ↓
                       Groq API (LLM)
```

Les **services** sont HTTP-agnostiques : ils lèvent des exceptions métier (ex : `EventNotFoundError`) que les routes traduisent en `HTTPException(404)`. Cela permet :
- Tests unitaires sans serveur HTTP (voir `tests/`)
- Réutilisation des services par les tools LLM

---

##  Sécurité

- **Aucune clé hardcodée** : tout passe par `.env` via `pydantic-settings`.
- `.env` est dans `.gitignore` (ne sera jamais commité).
- `.env.example` documente les variables sans leurs valeurs.
- Pour auditer : `git log -p | grep -E "gsk_[a-z0-9]{30,}"` doit être vide.

---

##  Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `GROQ_API_KEY` | *(obligatoire)* | Clé API Groq |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modèle LLM (doit supporter tool calling) |
| `DATABASE_URL` | `sqlite:///./data/assistant.db` | URL SQLAlchemy |
| `API_HOST` | `0.0.0.0` | Interface d'écoute |
| `API_PORT` | `8000` | Port HTTP |
| `LOG_LEVEL` | `INFO` | Niveau de logs (DEBUG/INFO/WARNING/ERROR) |

---
