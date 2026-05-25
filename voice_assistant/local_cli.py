import json
import os
import subprocess
from pathlib import Path

from voice_assistant.config import VOXYLN_PROJECT_DIR

_PROJECT_ROOT = Path(VOXYLN_PROJECT_DIR).resolve() if VOXYLN_PROJECT_DIR else Path(__file__).resolve().parent.parent


def run_local(query: str) -> str:
    clean_env = os.environ.copy()
    clean_env.pop("OPENCODE_SERVER_USERNAME", None)
    clean_env.pop("OPENCODE_SERVER_PASSWORD", None)
    try:
        result = subprocess.run(
            ["opencode", "run", "--format", "json", "--variant", "low", "--dir", str(_PROJECT_ROOT), query],
            capture_output=True, text=True, timeout=60,
            env=clean_env,
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"exit code {result.returncode}"
            return f"Error en opencode local: {error_msg}"
        for line in result.stdout.strip().splitlines():
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    text = event.get("part", {}).get("text", "")
                    if text:
                        return text.strip()
            except json.JSONDecodeError:
                continue
        return "No se obtuvo respuesta del CLI local."
    except subprocess.TimeoutExpired:
        return "La consulta local tardó demasiado. Intenta de nuevo."
    except FileNotFoundError:
        return "opencode no está instalado localmente."
    except Exception as e:
        return f"Error ejecutando consulta local: {e}"
