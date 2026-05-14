"""
Configuration centralisee de l'application.

Charge les variables depuis .env via pydantic-settings.
Expose un unique objet `settings` importe partout dans le code.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Schema typed de toutes les variables d'environnement.

    - Si une variable obligatoire manque dans .env, l'app echoue au
      demarrage avec une erreur Pydantic explicite (fail fast).
    - Les defauts correspondent aux valeurs de .env.example.
    """

    # --- LLM (Groq) ---
    groq_api_key: str  # Obligatoire — pas de defaut
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Base de donnees ---
    # SQLite par defaut en local. En prod (Render) : URL PostgreSQL fournie
    # automatiquement par la base managee (postgres://...).
    database_url: str = "sqlite:///./data/assistant.db"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Logging ---
    log_level: str = "INFO"

    # --- Auth / JWT ---
    # Cle de signature JWT. En prod, generer une valeur aleatoire forte
    # (ex: `openssl rand -hex 32`). Obligatoire.
    jwt_secret_key: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    # Duree de validite d'un access token en minutes (par defaut 24h).
    jwt_expire_minutes: int = 60 * 24

    # --- CORS ---
    # Liste d'origines autorisees, separees par des virgules.
    # "*" autorise tout (pratique pour un environnement de test).
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS en liste, gere le wildcard."""
        raw = self.cors_origins.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_url(cls, v: str) -> str:
        """
        Render fournit historiquement `postgres://...` mais SQLAlchemy
        attend `postgresql://...`. On normalise pour eviter un crash au boot.
        """
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # Configuration pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # GROQ_API_KEY ou groq_api_key : meme effet
        extra="ignore",         # ignore les variables .env non declarees ici
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retourne l'instance unique des settings (cache via lru_cache).
    Le .env n'est lu qu'une seule fois par processus.
    """
    return Settings()


# Instance globale — a importer partout ailleurs
# Ex : from src.core.config import settings
settings = get_settings()
