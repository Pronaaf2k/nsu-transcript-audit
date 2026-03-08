"""
main.py — NSU Transcript Audit CLI
Usage: python main.py [COMMAND]
"""
from __future__ import annotations

import os
import sys

# Allow sibling imports regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

import typer
from rich.console import Console

import auth as auth_module
import history as history_module
import scanner as scanner_module

app = typer.Typer(
    name="nsu-audit",
    help="NSU Transcript Audit CLI — scan transcripts and check graduation status.",
    add_completion=False,
)
console = Console()


@app.command()
def login():
    """Sign in with Google (opens browser)."""
    try:
        auth_module.login()
        console.print("[green]✓ Logged in successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def logout():
    """Sign out and remove local session."""
    auth_module.logout()
    console.print("[yellow]Logged out.[/yellow]")


@app.command()
def scan(
    file: str = typer.Argument(..., help="Path to transcript (PDF, JPG, PNG, CSV)"),
    program: str = typer.Option("CSE", "--program", "-p", help="Degree program code"),
):
    """Upload a transcript and run the graduation audit."""
    scanner_module.scan(file, program)


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of scans to show"),
):
    """List past transcript scans."""
    history_module.list_history(limit)


@app.command()
def report(
    scan_id: str = typer.Argument(..., help="Scan UUID to display in full"),
):
    """Show full JSON report for a specific scan."""
    history_module.show_report(scan_id)


if __name__ == "__main__":
    app()
