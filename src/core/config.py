"""
Configuration centralisee de l'application.

Charge les variables depuis .env via pydantic-settings.
Expose un unique objet `settings` importe partout dans le code.
"""
from functools import lru_cache
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
    database_url: str = "sqlite:///./data/assistant.db"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Logging ---
    log_level: str = "INFO"

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
