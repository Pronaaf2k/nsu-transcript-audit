"""
scanner.py — Upload a transcript and display the audit result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from auth import get_client

console = Console()

API_URL = os.environ.get("NEXT_PUBLIC_API_URL") or os.environ.get("GRADGATE_API_URL") or "http://localhost:8000"


def scan(file_path: str, program: str) -> None:
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found:[/red] {file_path}")
        raise SystemExit(1)

    supabase = get_client()
    session = supabase.auth.get_session()
    token = session.access_token

    console.print(f"[cyan]Uploading[/cyan] {path.name}…")

    console.print("[cyan]Running audit…[/cyan]")
    headers = {"Authorization": f"Bearer {token}"}

    if path.suffix.lower() == ".csv":
        res = httpx.post(
            f"{API_URL.rstrip('/')}/audit/run_csv",
            json={"csv_text": path.read_text(encoding="utf-8"), "program": program},
            headers={**headers, "Content-Type": "application/json"},
            timeout=60,
        )
    else:
        with path.open("rb") as f:
            files = {
                "file": (path.name, f, "application/octet-stream"),
            }
            data = {"program": program}
            res = httpx.post(
                f"{API_URL.rstrip('/')}/audit/image",
                files=files,
                data=data,
                headers=headers,
                timeout=120,
            )

    data = res.json()
    if not res.is_success:
        console.print(f"[red]Error:[/red] {data.get('detail', res.text)}")
        raise SystemExit(1)

    _print_result(data)


def _print_result(scan: dict) -> None:
    status = scan.get("graduation_status", "PENDING")
    color = "green" if status == "PASS" else "red" if status == "FAIL" else "yellow"

    console.print()
    console.rule("[bold]Audit Report[/bold]")

    t = Table(show_header=False, border_style="dim")
    t.add_column("Key", style="bold cyan", width=20)
    t.add_column("Value")
    t.add_row("Status",   f"[{color}]{status}[/{color}]")
    t.add_row("Program",  str(scan.get("program", "—")))
    t.add_row("Credits",  str(scan.get("total_credits", "—")))
    t.add_row("CGPA",     str(scan.get("cgpa", "—")))
    t.add_row("Scan ID",  scan.get("id", "—"))
    console.print(t)

    ar = scan.get("audit_result", {})
    deficiencies = ar.get("l3", {}).get("deficiencies", [])
    if deficiencies:
        console.print("\n[red]Deficiencies:[/red]")
        for d in deficiencies:
            console.print(f"  • {d}")
    console.print()
