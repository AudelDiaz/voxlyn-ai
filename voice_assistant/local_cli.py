import os
import subprocess
from pathlib import Path

from voice_assistant.config import VOXYLN_PROJECT_DIR

_PROJECT_ROOT = Path(VOXYLN_PROJECT_DIR).resolve() if VOXYLN_PROJECT_DIR else Path(__file__).resolve().parent.parent


def run_local(query: str) -> str:
    try:
        result = subprocess.run(
            ["opencode", "run", "--variant", "low", "--dir", str(_PROJECT_ROOT), query],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"exit code {result.returncode}"
            return f"Error en opencode local: {error_msg}"
        lines = result.stdout.strip().splitlines()
        response = "\n".join(line for line in lines if not line.startswith(">"))
        return response.strip()
    except subprocess.TimeoutExpired:
        return "La consulta local tardó demasiado. Intenta de nuevo."
    except FileNotFoundError:
        return "opencode no está instalado localmente."
    except Exception as e:
        return f"Error ejecutando consulta local: {e}"
