"""In-session voice commands that bypass the LLM."""

from opencode_client import OpencodeServer, OpencodeSession
from voice_assistant.config import VARIANT_NAMES

_VARIANT_ALIASES: dict[str, str] = {
    "default": "",
    "normal": "",
    "por defecto": "",
    "baja": "low",
    "bajo": "low",
    "rapido": "low",
    "rápido": "low",
    "media": "medium",
    "medio": "medium",
    "alta": "high",
    "alto": "high",
    "razonamiento": "high",
    "maxima": "max",
    "máxima": "max",
    "maximo": "max",
    "máximo": "max",
    "max": "max",
}


def _variant_label(key: str) -> str:
    return VARIANT_NAMES.get(key, key)


def handle_session_command(
    text: str, session: OpencodeSession, server: OpencodeServer
) -> str | None:
    """Check if *text* is a special command and handle it directly.

    Returns a response string if matched, or ``None`` to continue to the LLM.
    """
    t = text.lower().strip()

    if t in ("nueva conversacion", "nuevo chat", "reiniciar", "nueva conversación"):
        session.delete()
        session.create()
        return "Listo, nueva conversación creada."

    if t in ("lista sesiones", "listar sesiones", "muestra las sesiones"):
        sessions = OpencodeSession.list_all(server)
        if not sessions:
            return "No tienes sesiones guardadas."
        recent = sessions[-5:]
        titles = [s.get("title", "sin título") for s in recent]
        return "Tus sesiones: " + ", ".join(titles)

    if t.startswith("carga ") or t.startswith("abre "):
        query = t
        for prefix in ("carga ", "abre "):
            if t.startswith(prefix):
                query = t[len(prefix) :].strip()
                break
        found = OpencodeSession.find_by_title(server, query)
        if found:
            session.session_id = found["id"]
            session._msg_count = 0
            title = found.get("title", "sin título")
            return f"Sesión '{title}' cargada."
        return f"No encontré una sesión con ese nombre."

    if t.startswith("guarda como "):
        title = t[len("guarda como ") :].strip()
        session.rename(title)
        return f"Sesión guardada como '{title}'."

    if t in (
        "borra esta sesion",
        "borra esta sesión",
        "elimina sesion",
        "elimina sesión",
    ):
        session.delete()
        session.create()
        return "Sesión eliminada. Nueva sesión creada."

    if any(palabra in t for palabra in ("salir", "exit", "quit", "adiós", "adios")):
        return "__EXIT__"

    if t in ("logs", "ver logs", "show logs", "muestra logs", "abre logs", "ver registro"):
        return "__LOGS__"

    if t in ("lista variantes", "listar variantes", "que variantes hay", "muestra las variantes"):
        current = session.variant if hasattr(session, "variant") else ""
        desc = _variant_label(current)
        variants = "; ".join(f"{k} ({v})" for k, v in VARIANT_NAMES.items())
        return f"Las variantes disponibles son: {variants}. Actualmente tienes: {desc}."

    for alias, variant_key in _VARIANT_ALIASES.items():
        triggers = (f"variante {alias}", f"cambia variante a {alias}", f"cambia modo a {alias}")
        if any(t == p or t.startswith(p + " ") for p in triggers):
            session.variant = variant_key
            label = _variant_label(variant_key)
            return f"Variante cambiada a {label}."

    return None
