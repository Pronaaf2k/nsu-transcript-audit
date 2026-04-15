"""
local_storage.py — SQLite-based local storage for audit history
Works without Supabase. Stores audit results locally.
"""

import csv
import io
import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "audit_history.db")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audits (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TEXT NOT NULL,
            program TEXT NOT NULL,
            csv_text TEXT,
            total_credits REAL,
            cgpa REAL,
            graduation_status TEXT,
            result_json TEXT,
            source_type TEXT DEFAULT 'csv'
        )
    """)

    cursor.execute("PRAGMA table_info(audits)")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE audits ADD COLUMN user_id TEXT")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT NOT NULL,
            course_code TEXT,
            course_name TEXT,
            credits REAL,
            grade TEXT,
            semester TEXT,
            FOREIGN KEY (audit_id) REFERENCES audits(id)
        )
    """)
    
    conn.commit()
    conn.close()


def save_audit(
    user_id: str,
    csv_text: str,
    program: str,
    result: dict[str, Any],
    source_type: str = "csv"
) -> str:
    """Save an audit result and return the audit ID."""
    init_db()
    
    audit_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    total_credits = result.get("total_credits", result.get("cgpa", 0))
    cgpa = result.get("cgpa", 0)
    status = result.get("graduation_status", "UNKNOWN")
    result_json = json.dumps(result)
    
    conn = _get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO audits (id, user_id, created_at, program, csv_text, total_credits, cgpa, graduation_status, result_json, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (audit_id, user_id, created_at, program, csv_text, total_credits, cgpa, status, result_json, source_type))
    
    # Save individual courses
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        cursor.execute("""
            INSERT INTO courses (audit_id, course_code, course_name, credits, grade, semester)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            row.get("Course_Code", "").strip(),
            row.get("Course_Name", "").strip(),
            float(row.get("Credits", 0) or 0),
            row.get("Grade", "").strip(),
            row.get("Semester", "").strip()
        ))
    
    conn.commit()
    conn.close()
    
    return audit_id


def get_audit(audit_id: str, user_id: str) -> dict[str, Any] | None:
    """Get a single audit by ID."""
    init_db()
    
    conn = _get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM audits WHERE id = ? AND user_id = ?", (audit_id, user_id))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    cursor.execute("SELECT * FROM courses WHERE audit_id = ?", (audit_id,))
    courses = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    result = json.loads(row["result_json"])
    result["id"] = row["id"]
    result["created_at"] = row["created_at"]
    result["courses"] = courses
    
    return result


def get_audit_history(user_id: str, limit: int = 20, program: str | None = None) -> list[dict[str, Any]]:
    """Get recent audits."""
    init_db()
    
    conn = _get_db()
    cursor = conn.cursor()
    
    if program:
        cursor.execute("""
            SELECT id, created_at, program, total_credits, cgpa, graduation_status, source_type
            FROM audits
            WHERE user_id = ? AND program = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, program, limit))
    else:
        cursor.execute("""
            SELECT id, created_at, program, total_credits, cgpa, graduation_status, source_type
            FROM audits
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
    
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return rows


def delete_audit(audit_id: str, user_id: str) -> bool:
    """Delete an audit and its courses."""
    init_db()
    
    conn = _get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM audits WHERE id = ? AND user_id = ?", (audit_id, user_id))
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute("DELETE FROM courses WHERE audit_id = ?", (audit_id,))
        cursor.execute("DELETE FROM audits WHERE id = ? AND user_id = ?", (audit_id, user_id))

    deleted = exists
    conn.commit()
    conn.close()
    
    return deleted


def export_audits_csv(audit_ids: list[str] | None = None) -> str:
    """Export audits to CSV."""
    init_db()
    
    conn = _get_db()
    cursor = conn.cursor()
    
    if audit_ids:
        placeholders = ",".join("?" * len(audit_ids))
        cursor.execute(f"""
            SELECT * FROM audits WHERE id IN ({placeholders}) ORDER BY created_at DESC
        """, audit_ids)
    else:
        cursor.execute("SELECT * FROM audits ORDER BY created_at DESC")
    
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    return output.getvalue()


# Initialize DB on import
init_db()
