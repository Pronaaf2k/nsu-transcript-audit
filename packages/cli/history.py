"""
history.py — List past transcript scans for the authenticated user.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
import httpx
import os

from auth import get_client

console = Console()
API_URL = os.environ.get("NEXT_PUBLIC_API_URL") or os.environ.get("GRADGATE_API_URL") or "http://localhost:8000"


def list_history(limit: int = 20) -> None:
    try:
        supabase = get_client()
        session = supabase.auth.get_session()
        if not session or not getattr(session, "access_token", None):
            console.print("[yellow]No active session. Please login again.[/yellow]")
            return
        token = session.access_token

        res = httpx.get(
            f"{API_URL.rstrip('/')}/history",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        payload = None
        try:
            payload = res.json()
        except Exception:
            payload = None

        if not res.is_success:
            if res.status_code in (401, 403):
                console.print("[yellow]Session expired or unauthorized. Please logout and login again.[/yellow]")
                return
            detail = payload.get("detail", res.text) if isinstance(payload, dict) else res.text
            detail = str(detail).strip() or f"HTTP {res.status_code}"
            console.print(f"[red]Could not fetch history:[/red] {detail}")
            return

        scans = payload if isinstance(payload, list) else []
    except Exception as e:
        console.print(f"[red]Could not fetch history:[/red] {e}")
        return

    if not scans:
        console.print("[yellow]No transcript checked yet.[/yellow]")
        console.print("[dim]Run option 1 or 2 to create your first audit record.[/dim]")
        return

    t = Table(title="Scan History", border_style="dim")
    t.add_column("#",       style="dim", width=4)
    t.add_column("Date",    width=12)
    t.add_column("File",    max_width=24)
    t.add_column("Program", width=8)
    t.add_column("Credits", width=8, justify="right")
    t.add_column("CGPA",    width=6, justify="right")
    t.add_column("Status",  width=10)

    status_colors = {"PASS": "green", "FAIL": "red", "PENDING": "yellow"}

    for i, s in enumerate(scans, 1):
        if not isinstance(s, dict):
            continue
        st = s.get("graduation_status", "PENDING")
        col = status_colors.get(st, "white")
        created_at = str(s.get("created_at") or "")
        t.add_row(
            str(i),
            created_at[:10] if created_at else "-",
            s.get("file_name") or "(unknown)",
            s.get("program") or "—",
            str(s.get("total_credits") or "—"),
            str(s.get("cgpa") or "—"),
            f"[{col}]{st}[/{col}]",
        )

    console.print(t)


def show_report(scan_id: str) -> None:
    supabase = get_client()
    session = supabase.auth.get_session()
    token = session.access_token
    res = httpx.get(
        f"{API_URL.rstrip('/')}/history/{scan_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if res.status_code == 404:
        console.print(f"[red]Scan not found:[/red] {scan_id}")
        raise SystemExit(1)
    if not res.is_success:
        detail = res.json().get("detail", res.text)
        raise RuntimeError(f"Report request failed: {detail}")
    scan = res.json()
    if not scan:
        console.print(f"[red]Scan not found:[/red] {scan_id}")
        raise SystemExit(1)

    import json
    console.print_json(json.dumps(scan))
