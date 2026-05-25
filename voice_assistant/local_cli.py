import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_local(query: str) -> str:
    result = subprocess.run(
        ["opencode", "run", "--variant", "low", "--dir", str(_PROJECT_ROOT), query],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"opencode local CLI failed (exit {result.returncode}): {result.stderr}")
    lines = result.stdout.strip().splitlines()
    response = "\n".join(line for line in lines if not line.startswith(">"))
    return response.strip()
