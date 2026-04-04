"""
FastAPI server wrapping the NSU graduation audit engine (L1 / L2 / L3).
All OCR uses Tesseract — free, self-hosted, unlimited volume.

POST /audit
  Body: { "courses": [...], "program": "CSE" }
  Returns: full audit result JSON

POST /audit/csv
  Multipart: file=<csv>, program=<str>
  Returns: full audit result JSON

POST /audit/image
  Multipart: file=<image|pdf>, program=<str>
  Runs Tesseract OCR then audit. Single-scan interactive use.
  Returns: full audit result JSON + raw_ocr text

POST /batch/csv    — ZIP of CSVs, async job, poll /batch/{job_id}
POST /batch/images — ZIP of images/PDFs, Tesseract, async job
GET  /batch/{job_id} — job status + results

GET /health
  Returns: { "status": "ok", "tesseract": "<version>" }
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import pytesseract
    from PIL import Image
    TESSERACT_OK = True
except ImportError:
    TESSERACT_OK = False

# ── Path setup ────────────────────────────────────────────────────────────────
# Now importing from packages.core
import packages.core.audit_l1 as audit_l1
import packages.core.audit_l2 as audit_l2
import packages.core.audit_l3 as audit_l3
import packages.core.style as style

AUDIT_SRC = Path(__file__).parent.parent / "core"

# ── Security ──────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("AUDIT_API_KEY", "")


def _check_key(authorization: str | None):
    if not API_KEY:
        return  # dev mode — no key required
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="NSU Audit API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register batch router (ZIP uploads, async job queue)
from packages.api.batch import router as batch_router  # noqa: E402
app.include_router(batch_router)

# Import supabase client
from packages.api.supabase_client import save_transcript_and_audit


# ── Helpers ───────────────────────────────────────────────────────────────────

def _courses_to_csv(courses: list[dict[str, Any]]) -> str:
    """Convert a list of course dicts → CSV string the audit scripts can read."""
    buf = io.StringIO()
    fieldnames = ["Course_Code", "Credits", "Grade", "Semester", "Attempt"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for c in courses:
        writer.writerow({
            "Course_Code": c.get("course_id", c.get("Course_Code", "")),
            "Credits":     c.get("credits",   c.get("Credits", 0)),
            "Grade":       c.get("grade",     c.get("Grade", "")),
            "Semester":    c.get("semester",  c.get("Semester", "")),
            "Attempt":     c.get("attempt",   c.get("Attempt", 1)),
        })
    return buf.getvalue()


def _run_audit(csv_text: str, program: str) -> dict[str, Any]:
    """Write csv_text to a temp file, run all three audit levels, return results."""
    import importlib

    program_md = str(AUDIT_SRC / "program.md")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_text)
        tmp_path = f.name

    try:
        # ── L1: credit tally ──────────────────────────────────────────
        passed_courses, total_credits, rows_display = _l1_data(audit_l1, tmp_path)

        # ── L2: CGPA ──────────────────────────────────────────────────
        cgpa, waiver = _l2_data(audit_l2, tmp_path)

        # ── L3: full deficiency audit ─────────────────────────────────
        requirements = audit_l3.parse_program_knowledge(program_md, program)
        audit_result = audit_l3.audit_student(tmp_path, requirements, md_file=program_md)

        passed = (
            audit_result.get("graduation_eligible", False)
            if isinstance(audit_result, dict)
            else False
        )

        result = {
            "l1": {
                "total_credits": total_credits,
                "passed_courses": list(passed_courses),
            },
            "l2": {
                "cgpa":   round(cgpa, 2),
                "waiver": waiver,
            },
            "l3": audit_result,
            "program":           program,
            "total_credits":     total_credits,
            "cgpa":              round(cgpa, 2),
            "graduation_status": "PASS" if passed else "FAIL",
        }
        
        # Save to PostgreSQL
        save_transcript_and_audit(csv_text, program, 3, result)
        
        return result
    finally:
        os.unlink(tmp_path)


def _l1_data(audit_l1, csv_path: str):
    """Extract structured data from audit_l1 without printing."""
    passed_courses: set[str] = set()
    total_credits = 0.0

    GRADE_POINTS = {
        "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7, "D+": 1.3, "D": 1.0, "F": 0.0,
    }
    passed_best: dict[str, float] = {}
    rows_display = []

    with open(csv_path, mode="r") as infile:
        reader = csv.DictReader(infile)
        reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
        for row in reader:
            course  = row["Course_Code"].strip()
            grade   = row["Grade"].strip()
            try:    credits = float(row["Credits"])
            except: credits = 0.0

            pts = GRADE_POINTS.get(grade)

            if audit_l1.is_passing_grade(grade):
                if course not in passed_best:
                    total_credits += credits
                    passed_best[course] = pts if pts is not None else 0.0
                    passed_courses.add(course)
                    rows_display.append((course, credits, grade, "Counted"))
                else:
                    rows_display.append((course, credits, grade, "Retake (Ignored)"))
                    if pts is not None and pts > passed_best[course]:
                        passed_best[course] = pts
            else:
                rows_display.append((course, credits, grade, "Failed"))

    return passed_courses, total_credits, rows_display


def _l2_data(audit_l2, csv_path: str):
    """Extract CGPA from audit_l2 without printing."""
    # audit_l2.calculate_cgpa returns (cgpa, waiver_applied) or writes to stdout
    # We call the internal logic directly
    GRADE_POINTS = {
        "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7, "D+": 1.3, "D": 1.0, "F": 0.0,
    }
    best: dict[str, tuple[float, float]] = {}  # course -> (pts, credits)

    with open(csv_path, mode="r") as infile:
        reader = csv.DictReader(infile)
        reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
        for row in reader:
            course  = row["Course_Code"].strip()
            grade   = row["Grade"].strip()
            try:    credits = float(row["Credits"])
            except: credits = 0.0
            pts = GRADE_POINTS.get(grade, 0.0)
            if grade.upper() not in ("W", "I", "X"):
                if course not in best or pts > best[course][0]:
                    best[course] = (pts, credits)

    total_pts = sum(p * c for p, c in best.values())
    total_cr  = sum(c for _, c in best.values())
    cgpa = total_pts / total_cr if total_cr else 0.0
    return round(cgpa, 2), False


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _ocr_bytes_to_csv(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Run Tesseract on image/PDF bytes.
    Returns (csv_text, raw_ocr_text).
    Raises RuntimeError if Tesseract is not installed.
    """
    if not TESSERACT_OK:
        raise RuntimeError("Tesseract not installed on this server.")

    import re
    ext = Path(filename).suffix.lower()

    # ── Extract raw text ──────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(file_bytes)
        tmp_img = f.name

    try:
        if ext == ".pdf":
            from pdf2image import convert_from_path
            pages = convert_from_path(tmp_img, dpi=200)
            raw = "\n".join(
                pytesseract.image_to_string(p, config="--psm 6") for p in pages
            )
        else:
            img = Image.open(tmp_img)
            raw = pytesseract.image_to_string(img, config="--psm 6")
    finally:
        os.unlink(tmp_img)

    # ── Parse raw text → CSV rows ──────────────────────────────────────────────
    # Matches lines like: CSE115  3.0  A  Fall2022  (attempt is inferred)
    pattern = re.compile(
        r"(?P<code>[A-Z]{2,4}\d{3}[A-Z]?)"
        r"\s+(?P<credits>\d+\.?\d*)"
        r"\s+(?P<grade>[A-DF][+-]?|W|I)"
        r"(?:\s+(?P<semester>(?:Spring|Summer|Fall)\s*\d{4}))?",
        re.IGNORECASE,
    )
    attempt_counter: dict[str, int] = {}
    rows = []
    for line in raw.splitlines():
        m = pattern.search(line)
        if m:
            code = m.group("code").upper()
            attempt_counter[code] = attempt_counter.get(code, 0) + 1
            rows.append({
                "Course_Code": code,
                "Credits":     m.group("credits"),
                "Grade":       m.group("grade").upper(),
                "Semester":    (m.group("semester") or "").replace(" ", ""),
                "Attempt":     attempt_counter[code],
            })

    if not rows:
        return "", raw

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Course_Code", "Credits", "Grade", "Semester", "Attempt"])
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), raw


# ── Routes ────────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    courses: list[dict[str, Any]]
    program: str


@app.get("/health")
def health():
    version = "not installed"
    if TESSERACT_OK:
        try:
            version = pytesseract.get_tesseract_version().to_str()  # type: ignore[attr-defined]
        except Exception:
            version = "installed"
    return {"status": "ok", "tesseract": version}


@app.post("/audit/extract")
async def audit_extract(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    """
    Extract course rows from a PDF or image, returning raw CSV string for user review.
    """
    _check_key(authorization)
    file_bytes = await file.read()
    try:
        csv_text, raw_ocr = _ocr_bytes_to_csv(file_bytes, file.filename or "transcript.pdf")
        if not csv_text:
            raise HTTPException(
                status_code=422,
                detail="Tesseract could not extract any course data from this file."
            )
        return {"csv_text": csv_text, "raw_ocr": raw_ocr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit")
def audit_json(
    body: AuditRequest,
    authorization: str | None = Header(default=None),
):
    _check_key(authorization)
    csv_text = _courses_to_csv(body.courses)
    try:
        return _run_audit(csv_text, body.program)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AuditCsvRequest(BaseModel):
    csv_text: str
    program: str

@app.post("/audit/run_csv")
def audit_run_csv(
    body: AuditCsvRequest,
    authorization: str | None = Header(default=None),
):
    """
    Receives raw CSV string (after user edits) and runs the audit.
    """
    _check_key(authorization)
    try:
        return _run_audit(body.csv_text, body.program)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/csv")
async def audit_csv(
    file: UploadFile = File(...),
    program: str = Form(...),
    authorization: str | None = Header(default=None),
):
    _check_key(authorization)
    raw = await file.read()
    csv_text = raw.decode("utf-8-sig")
    try:
        return _run_audit(csv_text, program)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/image")
async def audit_image(
    file: UploadFile = File(...),
    program: str = Form(...),
    authorization: str | None = Header(default=None),
):
    """
    Upload a transcript image or PDF.
    Tesseract extracts course data, then runs the full L1/L2/L3 audit.
    """
    _check_key(authorization)
    file_bytes = await file.read()
    try:
        csv_text, raw_ocr = _ocr_bytes_to_csv(file_bytes, file.filename or "transcript.pdf")
        if not csv_text:
            raise HTTPException(
                status_code=422,
                detail="Tesseract could not extract any course data from this file. "
                       "Ensure the image is clear and right-side up.",
            )
        result = _run_audit(csv_text, program)
        result["raw_ocr"] = raw_ocr   # include for debugging
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
