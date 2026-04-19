"""
Tool LLM : synthese de document.

Prend un texte brut (compte-rendu, rapport, email) et produit une
synthese structuree (3-5 points cles, decisions, actions).

Le tool appelle Groq lui-meme (sans tool calling) avec un prompt
systeme contraignant le format de sortie.
"""
import json
import logging

from src.core.config import settings
from src.core.groq_client import get_groq_client

logger = logging.getLogger(__name__)

# Prompt systeme qui force la structure exigee par l'enonce.
_SYSTEM_PROMPT = """Tu es un assistant expert en synthese de documents professionnels.

Ta mission : produire une synthese structuree et exploitable d'un texte fourni.

FORMAT OBLIGATOIRE (en markdown) :

## Points cles
- (3 a 5 points essentiels extraits du document, concis et factuels)

## Decisions prises
- (liste des decisions actees dans le document, ou "Aucune decision identifiee.")

## Actions a suivre
- [Action concrete] — Responsable : [Nom ou fonction si mentionnes, sinon "non precise"]
- (ou "Aucune action identifiee." si absent)

REGLES :
- Reste factuel. N'invente jamais de decisions ou d'actions non mentionnees.
- Sois concis : 1-2 lignes par item maximum.
- Reponds en francais.
- Respecte STRICTEMENT la structure (titres, puces)."""

# Taille maximale du texte en entree (previent les depassements de contexte).
_MAX_INPUT_CHARS = 12000


def tool_summarize_document(text: str) -> str:
    """
    Tool LLM : synthetise un document en points cles, decisions et actions.

    Parametre :
      text : contenu brut du document (texte libre)

    Retourne un JSON string :
      succes -> {"success": true, "summary": "... markdown ..."}
      erreur -> {"success": false, "error": "message"}
    """
    logger.info("Tool call: summarize_document (taille=%d car.)", len(text) if text else 0)

    if not text or not text.strip():
        return json.dumps(
            {"success": False, "error": "Le texte a synthetiser est vide."},
            ensure_ascii=False,
        )

    # Troncature preventive si le texte est trop long.
    truncated = False
    if len(text) > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]
        truncated = True
        logger.warning("Texte tronque a %d caracteres.", _MAX_INPUT_CHARS)

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Voici le document a synthetiser :\n\n{text}"},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        summary = response.choices[0].message.content or ""

    except Exception as err:
        logger.exception("Echec de l'appel Groq pour summarize_document.")
        return json.dumps(
            {
                "success": False,
                "error": f"Erreur lors de la synthese : {type(err).__name__}",
            },
            ensure_ascii=False,
        )

    payload = {"success": True, "summary": summary}
    if truncated:
        payload["warning"] = f"Texte tronque a {_MAX_INPUT_CHARS} caracteres."
    return json.dumps(payload, ensure_ascii=False)
