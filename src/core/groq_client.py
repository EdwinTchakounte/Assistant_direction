"""
Client Groq partage par les tools et l'agent.

Un singleton (via lru_cache) : une seule instance par processus.
"""
from functools import lru_cache

from groq import Groq

from src.core.config import settings


@lru_cache
def get_groq_client() -> Groq:
    """Retourne une instance unique du client Groq initialise avec la cle API."""
    return Groq(api_key=settings.groq_api_key)
