"""LLM interaction via the OpenCode REST API."""

import sys

from opencode_client import OpencodeServer, OpencodeSession

from voice_assistant.commands import handle_session_command
from voice_assistant.config import SYSTEM_PROMPT
from voice_assistant.memory import save_turn, search_context, format_context


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
        session = OpencodeSession(server, system_prompt=SYSTEM_PROMPT)

    cmd_result = handle_session_command(text, session, server)
    if cmd_result is not None:
        if cmd_result == "__EXIT__":
            sys.exit(0)
        return cmd_result

    context = format_context(search_context(text))
    full_text = f"{context}\n\n{text}" if context else text

    response = session.send(full_text)
    save_turn(text, response)
    return response
