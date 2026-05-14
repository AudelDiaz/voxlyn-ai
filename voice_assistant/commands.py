"""In-session voice commands that bypass the LLM."""

from opencode_client import OpencodeServer, OpencodeSession


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

    return None
