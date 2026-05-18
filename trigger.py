#!/usr/bin/env python3
"""voxlyn-ai trigger: keyboard-shortcut client.

Usage:
    trigger.py           — send "record" (start/stop capture)
    trigger.py cancel    — send "cancel" (interrupt playback/processing)
    
Connects to the daemon's Unix socket, sends the command, and exits.
Designed to be bound to a keyboard shortcut.
"""

import socket
import subprocess
import sys
from pathlib import Path

SOCKET_PATH = Path.home() / ".voice-assistant" / "daemon.sock"


def main() -> None:
    """Connect to the daemon socket, send the command, and print the response."""
    cmd = sys.argv[1] if len(sys.argv) > 1 else "record"
    valid = ("record", "cancel")
    if cmd not in valid:
        print(f"Error: unknown command '{cmd}'. Valid: {'/'.join(valid)}", file=sys.stderr)
        sys.exit(1)

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
        sock.sendall(f"{cmd}\n".encode())
        response = sock.recv(64).decode().strip()
        if response == "busy":
            print("Daemon: busy (already processing)", file=sys.stderr)
        elif response == "ok":
            print(f"Daemon: {cmd} acknowledged", file=sys.stderr)
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
