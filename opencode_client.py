import os
import subprocess
import sys
import time
from typing import Optional

import requests

OPENCODE_URL = os.getenv("OPENCODE_URL", "http://localhost:4096")
OPENCODE_AUTO_START = os.getenv("OPENCODE_AUTO_START", "true").lower() == "true"


class OpencodeError(Exception):
    pass


class OpencodeServer:
    def __init__(self, url: str = OPENCODE_URL):
        self.url = url.rstrip("/")
        self.proc: Optional[subprocess.Popen] = None

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.url}/global/health", timeout=3)
            return r.ok
        except requests.RequestException:
            return False

    def ensure_running(self) -> None:
        if self.health():
            return
        if not OPENCODE_AUTO_START:
            raise OpencodeError(
                "OpenCode server not running. Start it: opencode serve"
            )
        port = 4096
        if ":" in self.url:
            port = int(self.url.split(":")[-1])
        self.proc = subprocess.Popen(
            ["opencode", "serve", "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if self.health():
                return
            time.sleep(0.5)
        raise OpencodeError("OpenCode server failed to start")

    def stop(self) -> None:
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


class OpencodeSession:
    def __init__(self, server: OpencodeServer, system_prompt: str = ""):
        self.server = server
        self.session_id: Optional[str] = None
        self.system_prompt = system_prompt
        self._msg_count = 0

    def create(self, title: str = "") -> str:
        body = {"title": title} if title else {}
        r = requests.post(f"{self.server.url}/session", json=body)
        r.raise_for_status()
        data = r.json()
        self.session_id = data["id"]
        self._msg_count = 0
        return self.session_id

    def delete(self) -> bool:
        if not self.session_id:
            return False
        try:
            r = requests.delete(f"{self.server.url}/session/{self.session_id}")
            return r.ok
        except requests.RequestException:
            return False
        finally:
            self.session_id = None
            self._msg_count = 0

    def rename(self, title: str) -> bool:
        if not self.session_id:
            return False
        try:
            r = requests.patch(
                f"{self.server.url}/session/{self.session_id}",
                json={"title": title},
            )
            return r.ok
        except requests.RequestException:
            return False

    def send(self, text: str, system: str = "") -> str:
        if not self.session_id:
            self.create()
        body = {
            "parts": [{"type": "text", "text": text}],
        }
        sp = system or self.system_prompt
        if sp:
            body["system"] = sp
        try:
            r = requests.post(
                f"{self.server.url}/session/{self.session_id}/message",
                json=body,
                timeout=180,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            if self.session_id and self._msg_count > 0:
                self.create()
                return self.send(text, system)
            raise OpencodeError(f"Failed to send message: {e}") from e
        data = r.json()
        self._msg_count += 1
        if self._msg_count == 1:
            title = text[:50].strip()
            self.rename(title)
        for p in data.get("parts", []):
            if p.get("type") == "text":
                return p.get("text", "")
        info = data.get("info", {})
        return info.get("content", "")

    @staticmethod
    def list_all(server: OpencodeServer) -> list[dict]:
        r = requests.get(f"{server.url}/session")
        r.raise_for_status()
        return r.json()

    @staticmethod
    def find_by_title(
        server: OpencodeServer, title_fragment: str
    ) -> Optional[dict]:
        sessions = OpencodeSession.list_all(server)
        lower = title_fragment.lower()
        matches = [
            s for s in sessions if lower in s.get("title", "").lower()
        ]
        if not matches:
            return None
        return max(matches, key=lambda s: s["time"]["updated"])
