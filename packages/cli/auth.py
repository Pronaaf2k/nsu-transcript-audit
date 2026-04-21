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
from supabase import create_client, Client, ClientOptions

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SESSION_FILE = Path.home() / ".nsu-audit" / "session.json"

_captured_auth_code: str | None = None
_captured_token: dict | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _captured_auth_code
        global _captured_token
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _captured_auth_code = params["code"][0]

        # Backward-compatible fallback if tokens are present in query params
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
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(flow_type="pkce", persist_session=True, auto_refresh_token=True),
    )
    if SESSION_FILE.exists():
        session = json.loads(SESSION_FILE.read_text())
        access_token = session.get("access_token", "")
        refresh_token = session.get("refresh_token", "")
        if not access_token or not refresh_token:
            try:
                SESSION_FILE.unlink()
            except Exception:
                pass
            if require_auth:
                raise RuntimeError("Session expired. Please login again.")
            return supabase
        try:
            supabase.auth.set_session(access_token, refresh_token)
        except Exception:
            try:
                SESSION_FILE.unlink()
            except Exception:
                pass
            if require_auth:
                raise RuntimeError("Session expired. Please login again.")
            return supabase
    elif require_auth:
        raise RuntimeError("Not logged in. Run: nsu-audit login")
    return supabase


def login() -> None:
    """Open browser, capture OAuth callback, persist session."""
    global _captured_auth_code
    global _captured_token
    _captured_auth_code = None
    _captured_token = None

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(flow_type="pkce", persist_session=True, auto_refresh_token=True),
    )
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

    if _captured_auth_code:
        resp = supabase.auth.exchange_code_for_session(
            {"auth_code": _captured_auth_code, "redirect_to": redirect_uri}
        )
        if resp and getattr(resp, "session", None):
            sess = resp.session
            _captured_token = {
                "access_token": sess.access_token,
                "refresh_token": sess.refresh_token,
            }

    if not _captured_token:
        session = supabase.auth.get_session()
        if session:
            _captured_token = {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
            }

    if not _captured_token:
        raise RuntimeError("Login timed out or was cancelled.")

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(_captured_token))


def logout() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
