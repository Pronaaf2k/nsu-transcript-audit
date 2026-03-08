"""
auth.py — Google OAuth login for the NSU Audit CLI.
Opens the browser, waits for the Supabase callback, and saves the
session to ~/.nsu-audit/session.json.
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SESSION_FILE = Path.home() / ".nsu-audit" / "session.json"

_captured_token: dict | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _captured_token
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Supabase sends access_token + refresh_token as query params
        if "access_token" in params:
            _captured_token = {
                "access_token": params["access_token"][0],
                "refresh_token": params.get("refresh_token", [""])[0],
            }
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Login successful! You may close this tab.</h2>")

    def log_message(self, *args):
        pass  # silence HTTP logs


def get_client(require_auth: bool = True) -> Client:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if SESSION_FILE.exists():
        session = json.loads(SESSION_FILE.read_text())
        supabase.auth.set_session(session["access_token"], session["refresh_token"])
    elif require_auth:
        raise RuntimeError("Not logged in. Run: nsu-audit login")
    return supabase


def login() -> None:
    """Open browser, capture OAuth callback, persist session."""
    global _captured_token
    _captured_token = None

    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    redirect_uri = "http://localhost:54320/callback"
    data = supabase.auth.sign_in_with_oauth(
        {"provider": "google", "options": {"redirect_to": redirect_uri}}
    )

    server = HTTPServer(("localhost", 54320), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    webbrowser.open(data.url)
    thread.join(timeout=120)
    server.server_close()

    if not _captured_token:
        raise RuntimeError("Login timed out or was cancelled.")

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(_captured_token))


def logout() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
