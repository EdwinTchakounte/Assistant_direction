# Assistant de Direction — Backend (Inov Consulting)

Backend FastAPI servant de support au **test technique Frontend** d'Inov Consulting.

Expose un agent IA (Groq + tool calling) avec :
- authentification JWT (`/auth/login`, `/users/me`),
- chat conversationnel avec mémoire (`/agent/chat`),
- gestion d'agenda et synthèse de documents via tools LLM.

---

## Endpoints exposés au frontend du test

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/auth/login` | Authentification utilisateur, renvoie un JWT |
| `GET` | `/users/me` | Profil de l'utilisateur connecté |
| `POST` | `/agent/chat` | Interaction avec l'assistant IA (auth requise) |

Documentation Swagger interactive : **`/docs`** (la racine `/` redirige vers `/docs`).

### Comptes de test fournis

5 comptes démo sont seedés automatiquement au démarrage si la table users est vide. **Tous partagent le même mot de passe : `Innov2026!`**.

| Email | Nom complet | Rôle | Département |
|---|---|---|---|
| `user1@inov-consulting.com` | Jean Mbarga | director | Direction generale |
| `user2@inov-consulting.com` | Sophie Ndongo | manager | Operations |
| `user3@inov-consulting.com` | Paul Eyenga | manager | Finance |
| `user4@inov-consulting.com` | Marie Atangana | user | Ressources humaines |
| `user5@inov-consulting.com` | Pierre Fouda | user | Tech |

### Exemples d'appels

**1. Login** — récupère un JWT
```bash
curl -X POST https://<host>/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user1@inov-consulting.com","password":"Innov2026!"}'
```
Réponse :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "user1@inov-consulting.com",
    "full_name": "Jean Mbarga",
    "role": "director",
    "status": "active",
    "department": "Direction generale",
    "phone": "+237 6 90 11 11 11",
    "avatar_url": null,
    "created_at": "2026-05-14T10:00:00"
  }
}
```

**2. Profil utilisateur**
```bash
curl https://<host>/users/me \
  -H "Authorization: Bearer <access_token>"
```

**3. Chat IA**
```bash
curl -X POST https://<host>/agent/chat \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "message": "Quels sont mes rendez-vous de demain ?"}'
```
Réponse :
```json
{
  "session_id": "7f3c1b0e-1a2b-4c5d-9e8f-0a1b2c3d4e5f",
  "response": "Vous avez deux rendez-vous demain : Comite de direction a 09:00 et Reunion equipe Tech a 14:30.",
  "tool_used": "get_agenda",
  "turn": 1
}
```

Pour conserver le contexte sur plusieurs tours, réutiliser le `session_id` reçu.

---

## Stack technique

| Composant | Choix |
|---|---|
| Backend | Python 3.11 + FastAPI |
| LLM | Groq API (`llama-3.3-70b-versatile`) — tool calling natif |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| DB | SQLite (local) / PostgreSQL (Render) — SQLAlchemy 2.x |
| Validation | Pydantic v2 + email-validator |
| Tests | Pytest |
| Conteneurisation | Docker + docker-compose |
| Déploiement | Render (blueprint `render.yaml`) |

---

## Lancement local

### Prérequis
- Docker + Docker Compose v2
- Une clé API Groq ([console.groq.com/keys](https://console.groq.com/keys))

### Étape 1 — Configurer `.env`
```bash
cp .env.example .env
```
Variables **obligatoires** à renseigner :
- `GROQ_API_KEY` — clé Groq ([console.groq.com/keys](https://console.groq.com/keys))
- `POSTGRES_PASSWORD` — mot de passe Postgres (fort)
- `JWT_SECRET_KEY` — `openssl rand -hex 32`

Les autres ont des valeurs par défaut sensées (voir `.env.example`).

### Étape 2 — Lancer
```bash
docker compose up -d --build
```

Démarre 2 containers :
- `assistant-direction-db` — PostgreSQL 16, port host **15432** (bindé sur `127.0.0.1`)
- `assistant-direction-api` — FastAPI, port host **8421** (bindé sur `127.0.0.1`)

> Les deux ports sont volontairement non-standards et bindés sur `127.0.0.1` :
> ils ne sont **PAS accessibles depuis l'extérieur**. Un reverse proxy
> (nginx/caddy) sur le serveur expose l'API en HTTPS (voir section déploiement).

### Vérification rapide
```bash
curl http://127.0.0.1:8421/health
# {"status":"ok","service":"assistant-direction","database":"connected"}
```

### Logs / arrêt / reset
```bash
docker compose logs -f api      # logs API en temps réel
docker compose down             # arrêt (DB conservée)
docker compose down -v          # arrêt + EFFACEMENT total de la DB
```

---

## Déploiement sur serveur dédié

Cible : sous-domaine `api-assistant-ia.horus-lab.com`.

> **Sous-domaine** : utiliser **tirets et minuscules**.
> Let's Encrypt refuse les certificats pour les hostnames avec underscore.

### Pré-requis sur le serveur

| Élément | Valeur / action |
|---|---|
| **DNS** record A | `api-assistant-ia.horus-lab.com` → IP publique du serveur |
| **Firewall** ouvert | `22/tcp` (SSH), `80/tcp`, `443/tcp` |
| **Firewall** fermé | `8421` (API) et `15432` (Postgres) — bindés sur 127.0.0.1 |
| **Software** | Docker ≥ 24, Docker Compose v2, **nginx** (déjà installé sur ton serveur), certbot |

### Procédure (3 étapes, ~5 minutes)

**Étape 1 — Cloner et copier le `.env`**
```bash
# Sur le serveur
git clone https://github.com/EdwinTchakounte/Assistant_direction.git
cd Assistant_direction
```

Depuis ton poste local, copier ton `.env` (déjà rempli avec la clé Groq et les secrets) :
```bash
# Sur ton poste local
scp .env utilisateur@serveur:/chemin/Assistant_direction/.env
```

**Étape 2 — Démarrer le stack**
```bash
# Sur le serveur
docker compose up -d --build
docker compose ps                  # 2 containers up + db healthy
curl http://127.0.0.1:8421/health  # doit renvoyer "ok"
```

**Étape 3 — Configurer nginx**
```bash
# Sur le serveur
sudo cp deploy/nginx/api-assistant-ia.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/api-assistant-ia.conf /etc/nginx/sites-enabled/
sudo nginx -t                      # vérifie syntaxe
sudo systemctl reload nginx

# Obtenir le certificat HTTPS (Let's Encrypt, gratuit, auto-renouvelé)
sudo certbot --nginx -d api-assistant-ia.horus-lab.com
```
Certbot modifie automatiquement le vhost pour ajouter SSL + redirection HTTP→HTTPS.

### Vérification finale
```bash
curl https://api-assistant-ia.horus-lab.com/health
# {"status":"ok","service":"assistant-direction","database":"connected"}
```
Documentation Swagger : `https://api-assistant-ia.horus-lab.com/docs`

### Mise à jour ultérieure
```bash
cd /chemin/vers/Assistant_direction
git pull
docker compose up -d --build      # rebuild + restart sans toucher à la DB
```

### Lancement sans Docker (dev local seulement)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Renseigner DATABASE_URL=postgresql://... ou laisser le défaut SQLite
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Tests

```bash
docker compose exec api pytest tests/ -v
```

12 tests unitaires couvrent le service agenda. Les tests d'auth restent à compléter.

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `GROQ_API_KEY` | *(obligatoire)* | Clé API Groq |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modèle LLM (doit supporter tool calling) |
| `POSTGRES_USER` | `assistant` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | *(obligatoire)* | Mot de passe PostgreSQL (fort en prod) |
| `POSTGRES_DB` | `assistant_direction` | Nom de la base PostgreSQL |
| `POSTGRES_PORT` | `15432` | Port host de Postgres (bindé sur 127.0.0.1) |
| `API_PORT` | `8421` | Port host de l'API (bindé sur 127.0.0.1) |
| `DATABASE_URL` | *(construite auto en compose)* | URL SQLAlchemy si lancement hors Docker |
| `JWT_SECRET_KEY` | *(obligatoire)* | Clé HS256 pour signer les JWT (`openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` | Algorithme de signature JWT |
| `JWT_EXPIRE_MINUTES` | `1440` | Durée de validité d'un access token |
| `CORS_ORIGINS` | `*` | Origines autorisées (séparées par virgules ou `*`) |
| `LOG_LEVEL` | `INFO` | Niveau de logs |

---

## Architecture

```
src/
├── main.py                     # FastAPI + lifespan + CORS + routers
├── core/
│   ├── config.py               # Settings Pydantic (.env)
│   ├── groq_client.py          # Singleton client Groq
│   └── security.py             # bcrypt + JWT helpers
├── models/
│   ├── db_models.py            # SQLAlchemy : User, Event, Session, Message
│   └── schemas.py              # Pydantic : LoginRequest, UserResponse, etc.
├── db/
│   ├── database.py             # engine + get_db + init_db
│   └── seed.py                 # seed_users + seed_events (idempotents)
├── services/                   # Logique métier, HTTP-agnostique
│   ├── user_service.py         # CRUD users + auth + get_current_user
│   ├── agenda_service.py       # CRUD agenda
│   ├── session_service.py      # Sessions liées au user
│   └── agent_service.py        # Boucle tool calling + mémoire
├── tools/                      # Tools exposés au LLM
│   ├── agenda_tool.py
│   ├── summarize_tool.py
│   └── registry.py
└── routes/                     # Endpoints HTTP
    ├── auth_routes.py          # POST /auth/login
    ├── user_routes.py          # GET /users/me
    ├── agent_routes.py         # POST /agent/chat (auth requise)
    ├── agenda_routes.py        # /agenda (CRUD)
    └── session_routes.py       # GET /session/{id}/history (auth requise)
```

### Séparation en couches
```
Client HTTP → routes → services → db_models / tools
                           ↓
                       Groq API (LLM)
```

Les **services** sont HTTP-agnostiques (lèvent des exceptions métier) → testables sans serveur HTTP, réutilisables par les tools LLM.

---

## Sécurité

- Aucune clé hardcodée : tout passe par `.env` / variables d'env Render.
- `.env` est dans `.gitignore`.
- Mots de passe stockés en hash bcrypt (jamais en clair).
- JWT signé HS256, secret rotable via `JWT_SECRET_KEY`.
- Sessions de chat isolées par utilisateur (403 si tentative de réutilisation cross-user).
- CORS configurable via `CORS_ORIGINS`.

---

## Pour les équipes frontend

Le test technique attend 3 écrans (Login, Profil utilisateur, Chat IA) consommant les endpoints listés en haut de ce README.

URL de production : *à communiquer une fois le déploiement Render effectué.*

Les candidats stockent le JWT (localStorage / cookie HttpOnly côté backend si besoin futur) et l'envoient sur chaque requête protégée via `Authorization: Bearer <token>`.
