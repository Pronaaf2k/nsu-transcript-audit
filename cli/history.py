"""
history.py — List past transcript scans for the authenticated user.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table

from auth import get_client

console = Console()


def list_history(limit: int = 20) -> None:
    supabase = get_client()
    resp = (
        supabase.table("transcript_scans")
        .select("id, created_at, file_name, program, total_credits, cgpa, graduation_status")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    scans = resp.data or []

    if not scans:
        console.print("[yellow]No scans found.[/yellow]")
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
        st = s.get("graduation_status", "PENDING")
        col = status_colors.get(st, "white")
        t.add_row(
            str(i),
            s["created_at"][:10],
            s.get("file_name") or "(unknown)",
            s.get("program") or "—",
            str(s.get("total_credits") or "—"),
            str(s.get("cgpa") or "—"),
            f"[{col}]{st}[/{col}]",
        )

    console.print(t)


def show_report(scan_id: str) -> None:
    supabase = get_client()
    resp = (
        supabase.table("transcript_scans")
        .select("*")
        .eq("id", scan_id)
        .single()
        .execute()
    )
    scan = resp.data
    if not scan:
        console.print(f"[red]Scan not found:[/red] {scan_id}")
        raise SystemExit(1)

    import json
    console.print_json(json.dumps(scan))
