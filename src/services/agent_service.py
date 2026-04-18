"""
Service agent : orchestration du tool calling avec Groq.

C'est le coeur du projet :
  - Gere la boucle de tool calling (jusqu'a MAX_TOOL_ITERATIONS iterations)
  - Maintient la memoire conversationnelle en relisant l'historique
    DB a chaque appel (5+ echanges supportes)
  - Capture `tool_used` pour la reponse (critere cle du bareme)

Principe de la boucle :
  1. On appelle Groq avec les messages + les tools disponibles
  2. Si la reponse contient des tool_calls -> on les execute,
     on ajoute les resultats aux messages, et on relance le LLM
  3. Si la reponse est du texte final -> on sort et on sauvegarde

Pour la memoire : on ne stocke en DB QUE les messages user +
assistant final. Les tool_calls intermediaires sont locaux au
tour en cours (pas necessaires pour reconstruire le contexte).
"""
import json
import logging
from datetime import date

from groq import BadRequestError
from sqlalchemy.orm import Session as SQLASession

from src.core.config import settings
from src.core.groq_client import get_groq_client
from src.models.schemas import ChatResponse
from src.services import session_service
from src.tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


# Garde-fou contre les boucles infinies de tool calls.
MAX_TOOL_ITERATIONS = 5

# Nombre de tentatives de retry en cas de tool_use_failed (bug
# ponctuel ou les modeles Llama emettent un format de tool call
# malforme). Cf. Groq API error code `tool_use_failed`.
MAX_TOOL_CALL_RETRIES = 2


def _build_system_prompt() -> str:
    """
    Prompt systeme de l'agent. La date du jour est injectee pour que
    le LLM puisse interpreter 'demain', 'vendredi', etc.
    """
    today = date.today().isoformat()
    return f"""Tu es l'assistant de direction d'un cadre dirigeant chez Inov Consulting.
Tu aides a gerer son agenda et a synthetiser des documents professionnels.

Date d'aujourd'hui : {today}.

Tu disposes de 3 outils (tools) :
  - get_agenda : consulter les evenements de l'agenda
  - create_event : planifier un nouveau rendez-vous
  - summarize_document : synthetiser un texte professionnel

REGLES :
- Reponds TOUJOURS en francais, de maniere concise et professionnelle.
- Quand l'utilisateur parle de dates relatives ("demain", "vendredi"),
  convertis-les en date absolue (YYYY-MM-DD) avant d'appeler un tool.
- Si une information essentielle manque pour appeler un tool (ex : heure
  d'une reunion), demande-la a l'utilisateur au lieu d'inventer.
- Utilise les tools a disposition plutot que d'inventer des reponses.
- Presente les evenements de facon claire : date, heure, titre, participants.
"""


def _history_to_groq_messages(messages) -> list[dict]:
    """
    Convertit l'historique DB (Message) en format messages Groq.
    On ne garde que les messages user et assistant finaux.
    """
    groq_msgs = []
    for m in messages:
        if m.role in ("user", "assistant"):
            groq_msgs.append({"role": m.role, "content": m.content})
    return groq_msgs


def _serialize_assistant_message(msg) -> dict:
    """
    Serialise un message assistant retourne par Groq (avec eventuels
    tool_calls) en dict reinjectable dans le prochain appel.
    """
    payload = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return payload


def _call_groq_with_retry(client, messages: list[dict]):
    """
    Appelle Groq avec retry automatique sur `tool_use_failed`.

    Les modeles Llama emettent parfois un format de tool call malforme
    (ex: '<function=get_agenda {...}>' au lieu du format structure).
    Ce probleme est transient : un nouveau sampling donne souvent
    une reponse propre.
    """
    last_err: Exception | None = None
    for attempt in range(MAX_TOOL_CALL_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.4,
            )
        except BadRequestError as err:
            # Detecte specifiquement le code `tool_use_failed`.
            body = getattr(err, "body", None) or {}
            err_dict = body.get("error", {}) if isinstance(body, dict) else {}
            if err_dict.get("code") == "tool_use_failed" and attempt < MAX_TOOL_CALL_RETRIES:
                logger.warning(
                    "tool_use_failed attempt %d/%d — retry",
                    attempt + 1,
                    MAX_TOOL_CALL_RETRIES + 1,
                )
                last_err = err
                continue
            raise
    # Ne devrait jamais arriver (la boucle raise ou return).
    raise last_err if last_err else RuntimeError("retry loop ended unexpectedly")


def chat(
    db: SQLASession,
    session_id: str | None,
    user_message: str,
) -> ChatResponse:
    """
    Traite un message utilisateur et retourne la reponse de l'agent.

    Etapes :
      1. Resoudre / creer la session.
      2. Charger l'historique pour conserver la memoire.
      3. Sauvegarder le message utilisateur.
      4. Boucler avec Groq : tool calling jusqu'a obtenir un texte final.
      5. Sauvegarder la reponse finale avec le tool_name (pour tool_used).
      6. Retourner ChatResponse(session_id, response, tool_used, turn).
    """
    # [1] Session
    session = session_service.get_or_create_session(db, session_id)

    # [2] Historique -> format Groq
    history = session_service.get_messages(db, session.id)
    groq_history = _history_to_groq_messages(history)

    # [3] Sauvegarde du message utilisateur AVANT l'appel LLM (pour qu'il
    #     soit toujours present meme si l'appel plante).
    session_service.append_message(db, session.id, "user", user_message)

    # [4] Construction des messages envoyes a Groq
    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt()},
        *groq_history,
        {"role": "user", "content": user_message},
    ]

    # [4bis] Boucle de tool calling
    client = get_groq_client()
    tool_used: str | None = None
    final_content: str | None = None

    try:
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info("Agent loop iteration %d", iteration + 1)
            response = _call_groq_with_retry(client, messages)
            msg = response.choices[0].message

            # Cas 1 : pas de tool call -> reponse finale
            if not msg.tool_calls:
                final_content = msg.content or ""
                break

            # Cas 2 : tool call(s) -> on les execute et on relance
            messages.append(_serialize_assistant_message(msg))
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                result_str = execute_tool(tool_name, tool_args, db=db)
                tool_used = tool_name  # on garde le DERNIER tool appele

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": result_str,
                    }
                )
        else:
            # Boucle epuisee sans reponse finale
            final_content = (
                "Desole, je n'ai pas pu finaliser ma reponse apres "
                f"{MAX_TOOL_ITERATIONS} tentatives. Reformulez svp."
            )

    except Exception as err:
        logger.exception("Echec de l'appel Groq.")
        final_content = (
            "Desole, une erreur technique m'empeche de traiter votre "
            f"demande ({type(err).__name__}). Reessayez dans un instant."
        )

    # [5] Sauvegarde de la reponse assistant finale avec tool_name
    session_service.append_message(
        db,
        session.id,
        "assistant",
        final_content or "",
        tool_name=tool_used,
    )

    # [6] Reponse structuree
    turn = session_service.count_user_turns(db, session.id)
    return ChatResponse(
        session_id=session.id,
        response=final_content or "",
        tool_used=tool_used,
        turn=turn,
    )
