"""
supabase_client.py - Direct HTTP-based Supabase client
Avoids supabase library compatibility issues with Python 3.14
"""
import os
import csv
import io
import json
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

HAS_SUPABASE = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

if SUPABASE_URL and SUPABASE_KEY:
    HAS_SUPABASE = True

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def _table_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def save_transcript_and_audit(
    csv_text: str,
    program: str,
    level: int,
    audit_result: dict[str, Any],
    student_id: str | None = None
) -> str | None:
    """
    Save audit results to Supabase.
    Returns scan_id on success, None on failure.
    """
    if not HAS_SUPABASE:
        print("Supabase not configured. Skipping save.")
        return None

    try:
        # 1. Save transcript courses
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = []
        for line in reader:
            rows.append({
                "student_id": student_id,
                "course": line.get("Course_Code", "").strip(),
                "credits": float(line.get("Credits", 0) or 0),
                "grade": line.get("Grade", "").strip(),
                "semester": line.get("Semester", "").strip()
            })

        scan_id = None

        # 2. Insert into transcript_scans
        cgpa = audit_result.get("cgpa", 0.0)
        total_credits = audit_result.get("total_credits", audit_result.get("l1", {}).get("totalCredits", 0))
        grad_status = audit_result.get("graduation_status", "PENDING")

        scan_data = {
            "user_id": student_id,
            "source_type": "csv",
            "program": program,
            "cgpa": cgpa,
            "total_credits": total_credits,
            "graduation_status": grad_status,
            "audit_result": audit_result
        }

        resp = requests.post(_table_url("transcript_scans"), headers=HEADERS, json=scan_data, timeout=15)
        if resp.status_code in (200, 201):
            result = resp.json()
            if isinstance(result, list):
                scan_id = result[0].get("id") if result else None
            elif isinstance(result, dict):
                scan_id = result.get("id")
        else:
            print(f"Failed to save transcript scan: {resp.status_code} {resp.text}")

        # 3. Insert audit_results
        audit_data = {
            "user_id": student_id,
            "scan_id": scan_id,
            "program": program,
            "audit_level": level,
            "cgpa": cgpa,
            "total_credits": total_credits,
            "graduation_status": grad_status,
            "missing_courses": audit_result.get("l3", {}).get("missing_courses", []),
            "advisories": audit_result.get("l3", {}).get("advisories", []),
            "result_json": audit_result
        }

        resp = requests.post(_table_url("audit_results"), headers=HEADERS, json=audit_data, timeout=15)
        if resp.status_code in (200, 201):
            print(f"Audit saved to Supabase successfully")
        else:
            print(f"Failed to save audit result: {resp.status_code} {resp.text[:200]}")

        return scan_id

    except Exception as e:
        print(f"Error saving to Supabase: {e}")
        return None


def get_scans(user_id: str | None = None, limit: int = 20) -> list[dict]:
    """Get transcript scans from Supabase."""
    if not HAS_SUPABASE:
        return []

    try:
        params = {"select": "*", "limit": limit, "order": "created_at.desc"}
        if user_id:
            params["user_id"] = f"eq.{user_id}"

        resp = requests.get(_table_url("transcript_scans"), headers=HEADERS, params=params)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching scans: {e}")

    return []


def get_audit_results(scan_id: str | None = None, limit: int = 20) -> list[dict]:
    """Get audit results from Supabase."""
    if not HAS_SUPABASE:
        return []

    try:
        params = {"select": "*", "limit": limit, "order": "created_at.desc"}
        if scan_id:
            params["scan_id"] = f"eq.{scan_id}"

        resp = requests.get(_table_url("audit_results"), headers=HEADERS, params=params)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching audit results: {e}")

    return []
