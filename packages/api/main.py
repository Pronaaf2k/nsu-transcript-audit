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

# Ensure repo root is importable before package imports.
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from packages.api.auth import CurrentUser

from packages.core.program_knowledge import (
    get_program_requirements,
    list_supported_programs,
    normalize_program_code,
)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

AUDIT_SRC = Path(__file__).parent.parent / "core"

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="NSU Audit API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register batch router (ZIP uploads, async job queue)
try:
    from packages.api.batch import router as batch_router  # noqa: E402
    app.include_router(batch_router)
except ImportError as e:
    print(f"Warning: Batch router not available: {e}")

# Import storage modules (local SQLite + optional Supabase)
from packages.api.local_storage import save_audit, get_audit, get_audit_history, delete_audit, save_feedback, get_feedback

try:
    from packages.api.supabase_client import save_transcript_and_audit
except ImportError:
    def save_transcript_and_audit(*args, **kwargs):
        pass  # Supabase not configured


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


def _run_audit(csv_text: str, program: str, user_id: str, concentration: str | None = None) -> dict[str, Any]:
    """Parse csv_text, run the Unified Auditor from GradTrace, return legacy + new results."""
    from packages.core.unified import UnifiedAuditor

    reader = csv.DictReader(io.StringIO(csv_text))
    # clean fieldnames
    reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
    
    rows = []
    for r in reader:
        rows.append({
            "course_code": r.get("Course_Code", "").strip(),
            "course_name": r.get("Course_Name", "").strip(),
            "credits": r.get("Credits", "0").strip(),
            "grade": r.get("Grade", "").strip(),
            "semester": r.get("Semester", "").strip(),
            "section": ""
        })

    result = UnifiedAuditor.run_from_rows(rows, program, concentration)

    eligible = result.get("level_3", {}).get("eligible", False) if result.get("level_3") else False
    deficiencies = result.get("level_3", {}).get("reasons", []) if result.get("level_3") else []
    total_cr = result.get("level_1", {}).get("credits_earned", 0) if result.get("level_1") else 0
    cgpa = result.get("level_2", {}).get("cgpa", 0.0) if result.get("level_2") else 0.0

    legacy = {
        "audit_result": {
            "l1": {
                "total_credits": total_cr,
                "passed_courses": [],
            },
            "l2": {
                "cgpa": cgpa,
                "waiver": False,
            },
            "l3": {
                "graduation_eligible": eligible,
                "deficiencies": deficiencies,
            },
            "graduation_status": "PASS" if eligible else "FAIL",
            "gradtrace": result
        },
        "program": program,
        "total_credits": total_cr,
        "cgpa": cgpa,
        "graduation_status": "PASS" if eligible else "FAIL",
    }
    
    # Save to PostgreSQL (optional - only if Supabase is configured)
    try:
        save_transcript_and_audit(csv_text, program, 3, legacy)
    except Exception:
        pass  # Supabase not configured, continue without saving
    
    # Save to local SQLite database (always works)
    try:
        audit_id = save_audit(user_id, csv_text, program, legacy, source_type="csv")
        legacy["id"] = audit_id
    except Exception as e:
        print(f"Warning: Failed to save locally: {e}")
    
    return legacy


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _parse_bytes_with_gemini(file_bytes: bytes, filename: str) -> str:
    from packages.core.pdf_parser import VisionParser
    import os, csv, io
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable missing!")
    
    rows = VisionParser.parse(file_bytes, api_key, filename=filename)
    if not rows:
        return ""
        
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Course_Code", "Course_Name", "Credits", "Grade", "Semester"])
    w.writeheader()
    for r in rows:
        w.writerow({
            "Course_Code": r.get("course_code", ""),
            "Course_Name": r.get("course_name", ""),
            "Credits": str(r.get("credits", "")),
            "Grade": r.get("grade", ""),
            "Semester": r.get("semester", "")
        })
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    courses: list[dict[str, Any]]
    program: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ocr": "gemini",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
    }


@app.get("/programs")
def get_programs():
    """
    List available programs from canonical program.md-backed config.
    """
    return {"programs": list_supported_programs()}


@app.get("/programs/{program_code}")
def get_program(program_code: str):
    """
    Return full requirement payload for a single program.
    """
    try:
        return get_program_requirements(program_code)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Program not found: {program_code}")


@app.post("/audit/extract")
async def audit_extract(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """
    Extract course rows from a PDF or image, returning raw CSV string for user review.
    """
    file_bytes = await file.read()
    try:
        csv_text = _parse_bytes_with_gemini(file_bytes, file.filename or "transcript.pdf")
        if not csv_text:
            raise HTTPException(
                status_code=422,
                detail="Gemini LLM could not extract any course data from this file."
            )
        return {"csv_text": csv_text, "raw_ocr": "Parsed by Gemini 2.5 Flash"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit")
def audit_json(
    current_user: CurrentUser,
    body: AuditRequest,
):
    program = normalize_program_code(body.program)
    csv_text = _courses_to_csv(body.courses)
    try:
        return _run_audit(csv_text, program, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AuditCsvRequest(BaseModel):
    csv_text: str
    program: str

@app.post("/audit/run_csv")
def audit_run_csv(
    current_user: CurrentUser,
    body: AuditCsvRequest,
):
    """
    Receives raw CSV string (after user edits) and runs the audit.
    """
    program = normalize_program_code(body.program)
    try:
        return _run_audit(body.csv_text, program, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/csv")
async def audit_csv(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    program: str = Form(...),
):
    program = normalize_program_code(program)
    raw = await file.read()
    csv_text = raw.decode("utf-8-sig")
    try:
        return _run_audit(csv_text, program, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/image")
async def audit_image(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    program: str = Form(...),
):
    """
    Upload a transcript image or PDF.
    Tesseract extracts course data, then runs the full L1/L2/L3 audit.
    """
    program = normalize_program_code(program)
    file_bytes = await file.read()
    try:
        csv_text = _parse_bytes_with_gemini(file_bytes, file.filename or "transcript.pdf")
        if not csv_text:
            raise HTTPException(
                status_code=422,
                detail="Gemini LLM could not extract any course data from this file. "
                       "Ensure the image is a valid academic transcript.",
            )
        result = _run_audit(csv_text, program, current_user)
        result["raw_ocr"] = "Parsed natively using Gemini 2.5 Flash."
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── History Endpoints ────────────────────────────────────────────────────────────

@app.get("/history")
def get_history(
    current_user: CurrentUser,
    limit: int = 20,
    program: str | None = None,
):
    """
    Get audit history.
    GET /history?limit=20&program=CSE
    """
    try:
        return get_audit_history(current_user, limit=limit, program=program)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{audit_id}")
def get_audit_by_id(
    current_user: CurrentUser,
    audit_id: str,
):
    """
    Get a specific audit by ID.
    """
    try:
        result = get_audit(audit_id, current_user)
        if not result:
            raise HTTPException(status_code=404, detail="Audit not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{audit_id}")
def delete_audit_by_id(
    current_user: CurrentUser,
    audit_id: str,
):
    """
    Delete a specific audit by ID.
    """
    try:
        deleted = delete_audit(audit_id, current_user)
        if not deleted:
            raise HTTPException(status_code=404, detail="Audit not found")
        return {"deleted": True, "id": audit_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackRequest(BaseModel):
    rating: int
    category: str
    feature_used: str
    improvements: str | None = None
    freeform: str | None = None
    audit_id: str | None = None


@app.post("/feedback")
def submit_feedback(
    current_user: CurrentUser,
    feedback: FeedbackRequest,
):
    """Submit user feedback (structured + freeform)."""
    try:
        feedback_id = save_feedback(current_user, feedback.model_dump())
        return {"id": feedback_id, "status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feedback")
def get_feedback_route(
    current_user: CurrentUser,
    limit: int = 100,
):
    """Get feedback history."""
    try:
        return get_feedback(current_user, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feedback/all")
def get_all_feedback(
    limit: int = 100,
):
    """Get all feedback (admin endpoint - no auth required for demo)."""
    try:
        return get_feedback(user_id=None, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
