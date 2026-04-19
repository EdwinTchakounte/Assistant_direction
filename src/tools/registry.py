"""
Registry central des tools exposes au LLM.

Expose :
  - TOOL_DEFINITIONS : liste des JSON Schemas (format OpenAI/Groq)
    passee au parametre `tools=` de client.chat.completions.create.
  - execute_tool(...) : dispatcher qui execute le bon tool Python
    a partir du nom et des arguments fournis par le LLM.

Les `description` des tools sont cruciales : elles guident la
decision du LLM sur QUAND appeler chaque outil. Elles doivent etre
precises, orientees cas d'usage, et mentionner les formats attendus.
"""
import json
import logging
from typing import Any

from sqlalchemy.orm import Session as SQLASession

from src.tools.agenda_tool import tool_create_event, tool_get_agenda
from src.tools.summarize_tool import tool_summarize_document

logger = logging.getLogger(__name__)


# =============================================================
# JSON Schemas exposes au LLM
# =============================================================

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_agenda",
            "description": (
                "Consulte l'agenda du directeur et retourne les evenements "
                "(reunions, rendez-vous, deplacements). A utiliser pour "
                "repondre a toute question sur le planning, les rendez-vous "
                "passes/futurs, ou pour verifier la disponibilite a une date. "
                "Exemples : 'Mes RDV demain', 'Planning de la semaine', "
                "'Qu'ai-je vendredi ?'. "
                "Sans parametre, retourne tous les evenements tries par date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": (
                            "Date exacte au format ISO YYYY-MM-DD. "
                            "Ex: 2026-04-18 pour le 18 avril 2026."
                        ),
                    },
                    "range": {
                        "type": "string",
                        "enum": ["week"],
                        "description": (
                            "Plage temporelle. 'week' = les 7 prochains jours "
                            "a partir d'aujourd'hui."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": (
                "Cree un nouvel evenement (reunion, rendez-vous) dans l'agenda "
                "du directeur. A utiliser quand l'utilisateur demande de "
                "PLANIFIER, AJOUTER, RESERVER ou PROGRAMMER un nouveau rendez-vous. "
                "Exemples : 'Planifie une reunion vendredi 10h avec l'equipe tech', "
                "'Ajoute un dejeuner client demain midi'. "
                "Si une information obligatoire manque (titre, date, heure), "
                "demande-la a l'utilisateur avant d'appeler ce tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": (
                            "Titre court et explicite de l'evenement. "
                            "Ex: 'Reunion equipe tech', 'Comite de direction'."
                        ),
                    },
                    "date": {
                        "type": "string",
                        "description": (
                            "Date de l'evenement au format ISO YYYY-MM-DD. "
                            "Convertis les expressions naturelles comme 'demain' "
                            "ou 'vendredi' en date absolue avant d'appeler le tool."
                        ),
                    },
                    "time": {
                        "type": "string",
                        "description": (
                            "Heure au format 24h HH:MM. Ex: '10:00', '14:30'."
                        ),
                    },
                    "participants": {
                        "type": "string",
                        "description": (
                            "Liste des participants separes par des virgules. "
                            "Ex: 'DG, DAF, DSI' ou 'Equipe tech'."
                        ),
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes ou contexte additionnel sur l'evenement.",
                    },
                },
                "required": ["title", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": (
                "Synthetise un document (compte-rendu, rapport, email, note) "
                "en extrayant points cles, decisions prises et actions a suivre "
                "avec responsables. A utiliser quand l'utilisateur fournit un "
                "texte et demande un resume, une synthese, ou les points "
                "principaux. Exemples : 'Resume ce compte-rendu', "
                "'Quels sont les points cles de ce mail ?', "
                "'Synthetise ce rapport'. "
                "Retourne une synthese structuree en markdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": (
                            "Contenu brut du document a synthetiser. "
                            "Texte integral, pas un resume pre-mache."
                        ),
                    },
                },
                "required": ["text"],
            },
        },
    },
]


# =============================================================
# Dispatcher : execute le bon tool selon le nom fourni par le LLM
# =============================================================

def execute_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    db: SQLASession,
) -> str:
    """
    Execute un tool a partir de son nom et des arguments fournis par le LLM.

    Parametres :
      name       : nom du tool (doit matcher TOOL_DEFINITIONS)
      arguments  : dict d'arguments extraits du tool_call du LLM
      db         : session DB (injectee, invisible pour le LLM)

    Retourne une string (JSON) qui sera renvoyee au LLM comme
    resultat du tool_call.

    En cas d'erreur (tool inconnu, arguments invalides), retourne
    un JSON d'erreur pour que le LLM puisse reagir proprement.
    """
    logger.info("Dispatch tool=%s args_keys=%s", name, list(arguments.keys()))

    try:
        if name == "get_agenda":
            return tool_get_agenda(db, **arguments)

        if name == "create_event":
            return tool_create_event(db, **arguments)

        if name == "summarize_document":
            return tool_summarize_document(**arguments)

        # Tool inconnu
        return json.dumps(
            {"success": False, "error": f"Outil inconnu : {name}"},
            ensure_ascii=False,
        )

    except TypeError as err:
        # Arguments manquants ou en trop
        logger.warning("Arguments invalides pour %s : %s", name, err)
        return json.dumps(
            {
                "success": False,
                "error": f"Arguments invalides pour {name} : {err}",
            },
            ensure_ascii=False,
        )
    except Exception as err:
        logger.exception("Erreur inattendue lors de l'execution de %s", name)
        return json.dumps(
            {
                "success": False,
                "error": f"Erreur interne ({type(err).__name__}) lors de l'execution de {name}.",
            },
            ensure_ascii=False,
        )
