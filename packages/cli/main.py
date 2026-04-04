"""
main.py — NSU Transcript Audit CLI
Usage: python main.py [COMMAND]
"""
from __future__ import annotations

import os
import sys
import argparse

# Allow sibling imports regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

import typer
from rich.console import Console

import auth as auth_module
import history as history_module
import scanner as scanner_module
import audit

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


@app.command()
def audit(
    transcript: str = typer.Argument(..., help="Path to transcript CSV file"),
    level: int = typer.Option(3, "--level", "-l", help="Audit level (1, 2, 3, or full)"),
    program: str = typer.Option("CSE", "--program", "-p", help="Program code (CSE, BBA, ETE, ENV, ENG, ECO)"),
    waivers: str = typer.Option("", "--waivers", "-w", help="Comma-separated course codes to waive"),
):
    """Run L1/L2/L3 audit on a transcript CSV file."""
    program_file = os.path.join(os.path.dirname(__file__), "program.md")
    
    if not os.path.exists(transcript):
        console.print(f"[red]Error: File not found: {transcript}[/red]")
        raise typer.Exit(1)
    
    waiver_list = [w.strip() for w in waivers.split(',') if w.strip()] if waivers else None
    
    try:
        if level == 1:
            from audit.audit_l1 import calculate_credits
            calculate_credits(transcript)
        elif level == 2:
            from audit.audit_l2 import calculate_cgpa
            calculate_cgpa(transcript, waivers=waiver_list)
        elif level == 3:
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
