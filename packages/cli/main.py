"""
main.py — NSU Transcript Audit CLI
Usage: python main.py [COMMAND]
"""
from __future__ import annotations

import os
import sys
import argparse
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

import audit

app = typer.Typer(
    name="nsu-audit",
    help="NSU Transcript Audit CLI — scan transcripts and check graduation status.",
    add_completion=False,
)
console = Console()

PROGRAM_CODES = ["CSE", "BBA", "ETE", "ENV", "ENG", "ECO"]
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


def _draw_menu() -> None:
    console.clear()
    console.print(Panel("[bold cyan]NSU Transcript Audit[/bold cyan]\nSingle place for login, scan, audit, and history", border_style="cyan"))
    console.print(f"Session: {_session_status_text()}\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Action", style="white")
    table.add_row("1", "Login with Google")
    table.add_row("2", "Scan transcript (upload + audit)")
    table.add_row("3", "Run local CSV audit (L1/L2/L3/full)")
    table.add_row("4", "View scan history")
    table.add_row("5", "View scan report by ID")
    table.add_row("6", "Logout")
    table.add_row("0", "Exit")
    console.print(table)


def _menu_loop() -> None:
    while True:
        _draw_menu()
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5", "6", "0"], default="2")

        try:
            if choice == "1":
                login()
            elif choice == "2":
                file_path = Prompt.ask("Transcript path (PDF/JPG/PNG/CSV)").strip()
                program = _prompt_program()
                scan(file_path, program)
            elif choice == "3":
                transcript = Prompt.ask("CSV transcript path").strip()
                level = Prompt.ask("Audit level", choices=["1", "2", "3", "full"], default="3")
                program = _prompt_program()
                waivers = Prompt.ask("Waivers (comma-separated, optional)", default="").strip()
                audit(transcript=transcript, level=level, program=program, waivers=waivers)
            elif choice == "4":
                limit_str = Prompt.ask("History rows", default="20")
                limit = int(limit_str) if limit_str.isdigit() else 20
                history(limit=limit)
            elif choice == "5":
                scan_id = Prompt.ask("Scan ID").strip()
                report(scan_id)
            elif choice == "6":
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
):
    """Upload a transcript and run the graduation audit."""
    import scanner as scanner_module
    scanner_module.scan(file, program)


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


@app.command()
def audit(
    transcript: str = typer.Argument(..., help="Path to transcript CSV file"),
    level: str = typer.Option("3", "--level", "-l", help="Audit level (1, 2, 3, or full)"),
    program: str = typer.Option("CSE", "--program", "-p", help="Program code (CSE, BBA, ETE, ENV, ENG, ECO)"),
    waivers: str = typer.Option("", "--waivers", "-w", help="Comma-separated course codes to waive"),
):
    """Run L1/L2/L3 audit on a transcript CSV file."""
    program_file = os.path.join(os.path.dirname(__file__), "program.md")
    
    if not os.path.exists(transcript):
        console.print(f"[red]Error: File not found: {transcript}[/red]")
        raise typer.Exit(1)
    
    waiver_list = [w.strip() for w in waivers.split(',') if w.strip()] if waivers else None
    level = str(level).strip().lower()
    
    try:
        if level == "1":
            from audit.audit_l1 import calculate_credits
            calculate_credits(transcript)
        elif level == "2":
            from audit.audit_l2 import calculate_cgpa
            calculate_cgpa(transcript, waivers=waiver_list)
        elif level == "3":
            audit.run_level3(transcript, program, program_file)
        elif level == 'full':
            audit.run_full(transcript, program, program_file, waiver_list)
        else:
            console.print(f"[red]Error: Invalid level. Use 1, 2, 3, or 'full'.[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
