"""LLM interaction via the OpenCode REST API."""

import sys

from opencode_client import OpencodeServer, OpencodeSession

from voice_assistant.commands import handle_session_command
from voice_assistant.config import (
    AUTO_VARIANT_KEYWORDS,
    SYSTEM_PROMPT,
    VARIANT,
)
from voice_assistant.memory import save_turn, search_context, format_context


def _infer_variant(text: str, configured: str) -> str:
    """Return a higher variant when the query looks complex.

    If the user already chose ``high`` or ``max``, respect that choice.
    Otherwise bump to ``high`` temporarily for complex-looking queries.
    """
    if configured in ("high", "max"):
        return configured
    lower = text.lower()
    if any(kw in lower for kw in AUTO_VARIANT_KEYWORDS):
        return "high"
    if len(text) > 120:
        return "medium"
    return configured


def get_response(
    text: str,
    server: OpencodeServer | None = None,
    session: OpencodeSession | None = None,
) -> str:
    """Send *text* to the LLM and return the response.

    Creates or reuses an *server* and *session* pair:

    * If a **command** is detected (e.g. "nueva conversacion") it is handled
      locally without calling the LLM.
    * Otherwise the assistant searches mempalace for relevant context,
      sends the combined message to the LLM via OpenCode, saves the
      conversation turn, and returns the response.
    """
    if server is None:
        server = OpencodeServer()
        server.ensure_running()
    if session is None:
        session = OpencodeSession(server, system_prompt=SYSTEM_PROMPT, variant=VARIANT)

    cmd_result = handle_session_command(text, session, server)
    if cmd_result is not None:
        if cmd_result == "__EXIT__":
            sys.exit(0)
        return cmd_result

    context = format_context(search_context(text))
    full_text = f"{context}\n\n{text}" if context else text

    variant = _infer_variant(text, session.variant)
    response = session.send(full_text, variant=variant)
    save_turn(text, response)
    return response
