"""
parser.py — Normalise a raw NSU transcript into the canonical
list-of-dicts format expected by the audit runners.

Input CSV columns (case-insensitive, trimmed):
  CourseID | CourseName | Credits | Grade | Semester | Attempt

Output: list of dicts with keys:
  course_id, course_name, credits, grade, semester, attempt
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any

# Map common header aliases → canonical key
_HEADER_MAP = {
    "courseid": "course_id",
    "course id": "course_id",
    "course_id": "course_id",
    "coursename": "course_name",
    "course name": "course_name",
    "course_name": "course_name",
    "credits": "credits",
    "credit": "credits",
    "credit hours": "credits",
    "grade": "grade",
    "letter grade": "grade",
    "semester": "semester",
    "term": "semester",
    "attempt": "attempt",
    "attempt no": "attempt",
    "attempt_no": "attempt",
}

_REQUIRED = {"course_id", "credits", "grade"}


def parse_csv_transcript(raw: str | bytes) -> list[dict[str, Any]]:
    """
    Parse a raw CSV string (or bytes) into a list of normalised course dicts.
    Raises ValueError if required columns are missing.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")  # strip BOM if present

    reader = csv.DictReader(io.StringIO(raw.strip()))
    if reader.fieldnames is None:
        raise ValueError("CSV has no headers")

    # Build header remapping
    col_map: dict[str, str] = {}
    for raw_col in reader.fieldnames:
        canonical = _HEADER_MAP.get(raw_col.strip().lower())
        if canonical:
            col_map[raw_col] = canonical

    missing = _REQUIRED - set(col_map.values())
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    rows: list[dict[str, Any]] = []
    for row in reader:
        entry: dict[str, Any] = {
            "course_id": "",
            "course_name": "",
            "credits": 0,
            "grade": "",
            "semester": "",
            "attempt": 1,
        }
        for raw_col, canonical in col_map.items():
            val = (row.get(raw_col) or "").strip()
            if canonical == "credits":
                entry[canonical] = _parse_float(val)
            elif canonical == "attempt":
                entry[canonical] = int(val) if val.isdigit() else 1
            else:
                entry[canonical] = val
        rows.append(entry)

    return rows


def _parse_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
