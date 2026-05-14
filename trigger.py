#!/usr/bin/env python3
"""voxlyn-ai trigger: keyboard-shortcut client.

Connects to the daemon's Unix socket, sends a ``record`` command,
and exits. Designed to be bound to a keyboard shortcut.
"""

import socket
import subprocess
import sys
from pathlib import Path

SOCKET_PATH = Path.home() / ".voice-assistant" / "daemon.sock"


def main() -> None:
    """Connect to the daemon socket and request a recording cycle."""
    if not SOCKET_PATH.exists():
        print("Error: Voice Assistant daemon is not running.", file=sys.stderr)
        try:
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "critical",
                    "Voice Assistant",
                    "Daemon not running",
                ],
                timeout=2,
            )
        except Exception:
            pass
        sys.exit(1)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect(str(SOCKET_PATH))
        sock.sendall(b"record\n")
        response = sock.recv(64).decode().strip()
        if response == "busy":
            print("Daemon: busy (already processing)", file=sys.stderr)
        elif response == "ok":
            print("Daemon: recording...", file=sys.stderr)
        else:
            print(f"Daemon: {response}", file=sys.stderr)
    except socket.timeout:
        print("Error: connection timed out", file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        print("Error: daemon refused connection", file=sys.stderr)
        sys.exit(1)
    finally:
        sock.close()


if __name__ == "__main__":
    main()
