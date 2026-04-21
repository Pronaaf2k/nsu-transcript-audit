"""
main.py — NSU Transcript Audit CLI
Usage: python main.py [COMMAND]
"""
from __future__ import annotations

import os
import sys
import argparse
import json
import base64
from pathlib import Path

# Allow sibling imports regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(
    name="nsu-audit",
    help="NSU Transcript Audit CLI — scan transcripts and check graduation status.",
    add_completion=False,
)
console = Console()

PROGRAM_CODES = ["CSE", "BBA", "BBA-OLD", "ETE", "ENV", "ENG", "ECO"]
SESSION_FILE = Path.home() / ".nsu-audit" / "session.json"


def _prompt_program(default: str = "CSE") -> str:
    while True:
        value = Prompt.ask(
            "Program code",
            default=default,
        ).strip().upper()
        if value in PROGRAM_CODES:
            return value
        console.print(f"[yellow]Use one of:[/yellow] {', '.join(PROGRAM_CODES)}")


def _session_status_text() -> str:
    return "[green]Logged in[/green]" if SESSION_FILE.exists() else "[yellow]Not logged in[/yellow]"


def _session_email() -> str | None:
    if not SESSION_FILE.exists():
        return None
    try:
        session = json.loads(SESSION_FILE.read_text())
        token = session.get("access_token", "")
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        claims = json.loads(decoded)
        return claims.get("email")
    except Exception:
        return None


def _draw_menu() -> None:
    console.clear()
    console.print(Panel("[bold cyan]NSU Transcript Audit[/bold cyan]\nSingle place for login, scan, audit, and history", border_style="cyan"))
    logged_in = SESSION_FILE.exists()
    console.print(f"Session: {_session_status_text()}\n")
    if logged_in:
        email = _session_email() or "unknown user"
        console.print(f"Account: [cyan]{email}[/cyan]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="white")
    if logged_in:
        table.add_row("1", "Scan transcript (audit L1/L2/L3)")
        table.add_row("2", "Run CSV audit (L1/L2/L3 + saved)")
        table.add_row("3", "View scan history (online scans)")
        table.add_row("4", "Logout")
    else:
        table.add_row("1", "Login with Google")
    table.add_row("0", "Exit")
    console.print(table)


def _menu_loop() -> None:
    while True:
        _draw_menu()
        logged_in = SESSION_FILE.exists()
        choices = ["1", "2", "3", "4", "0"] if logged_in else ["1", "0"]
        default_choice = "1"
        choice = Prompt.ask("Choose an option", choices=choices, default=default_choice)

        try:
            if choice == "1" and not logged_in:
                login()
            elif choice == "1" and logged_in:
                file_path = Prompt.ask("Transcript path (PDF/JPG/PNG/CSV)").strip()
                program = _prompt_program()
                level = int(Prompt.ask("Audit level", choices=["1", "2", "3"], default="3"))
                scan(file_path, program, level)
            elif choice == "2" and logged_in:
                transcript = Prompt.ask("CSV transcript path").strip()
                program = _prompt_program()
                level = int(Prompt.ask("Audit level", choices=["1", "2", "3"], default="3"))
                scan(transcript, program, level)
            elif choice == "3" and logged_in:
                limit_str = Prompt.ask("History rows", default="20")
                limit = int(limit_str) if limit_str.isdigit() else 20
                history(limit=limit)
            elif choice == "4" and logged_in:
                logout()
            else:
                console.print("[cyan]Goodbye.[/cyan]")
                return
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

        Prompt.ask("\nPress Enter to return to menu", default="")


@app.callback(invoke_without_command=True)
def entrypoint(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _menu_loop()


@app.command("menu")
def menu_command():
    """Open interactive menu."""
    _menu_loop()


@app.command()
def login():
    """Sign in with Google (opens browser)."""
    try:
        import auth as auth_module
        auth_module.login()
        console.print("[green]✓ Logged in successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def logout():
    """Sign out and remove local session."""
    import auth as auth_module
    auth_module.logout()
    console.print("[yellow]Logged out.[/yellow]")


@app.command()
def scan(
    file: str = typer.Argument(..., help="Path to transcript (PDF, JPG, PNG, CSV)"),
    program: str = typer.Option("CSE", "--program", "-p", help="Degree program code"),
    level: int = typer.Option(3, "--level", "-l", min=1, max=3, help="Audit level (1, 2, 3)"),
):
    """Upload a transcript and run the graduation audit."""
    import scanner as scanner_module
    scanner_module.scan(file, program, level)


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of scans to show"),
):
    """List past transcript scans."""
    import history as history_module
    history_module.list_history(limit)


@app.command()
def report(
    scan_id: str = typer.Argument(..., help="Scan UUID to display in full"),
):
    """Show full JSON report for a specific scan."""
    import history as history_module
    history_module.show_report(scan_id)


@app.command("audit")
def audit_command(
    transcript: str = typer.Argument(..., help="Path to transcript CSV file"),
    level: int = typer.Option(3, "--level", "-l", min=1, max=3, help="Audit level (1, 2, 3)"),
    program: str = typer.Option("CSE", "--program", "-p", help="Program code (CSE, BBA, ETE, ENV, ENG, ECO)"),
    waivers: str = typer.Option("", "--waivers", "-w", help="Ignored"),
):
    """Run CSV audit via backend so result is stored in history."""
    if waivers.strip():
        console.print("[yellow]Note:[/yellow] --waivers is ignored.")
    scan(transcript, program, level)


if __name__ == "__main__":
    app()
