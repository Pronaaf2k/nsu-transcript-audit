"""
batch.py — Bulk transcript processing endpoints.

POST /batch/csv
  Accepts a ZIP of CSV files or multiple CSVs in a multipart form.
  Runs all audits concurrently and returns a summary + per-scan results.

POST /batch/images
  Accepts a ZIP of image/PDF files.
  Uses Tesseract OCR (free, unlimited, self-hosted) → audit pipeline.
  Designed for 10k–20k transcript bulk runs.

GET /batch/{job_id}
  Returns the current status of an async batch job.
"""
from __future__ import annotations

import asyncio
import csv
import io
import os
import tempfile
import time
import uuid
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

# ── In-memory job store (replace with Redis for multi-instance) ───────────────
_JOBS: dict[str, dict] = {}

router = APIRouter(prefix="/batch", tags=["batch"])

# ── OCR helpers ───────────────────────────────────────────────────────────────

def _ocr_image_file(path: str) -> str:
    """Use Gemini to OCR a single image or PDF page. Returns CSV text."""
    import os
    from packages.core.pdf_parser import VisionParser
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is required for OCR")
    
    with open(path, "rb") as f:
        file_bytes = f.read()
    
    rows = VisionParser.parse(file_bytes, api_key, filename=path)
    
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


def _ocr_text_to_csv(raw_text: str) -> str:
    """
    Fallback: Best-effort convert raw text to the audit CSV format.
    Looks for lines that look like: COURSEXX  3.0  A  Fall2022
    """
    import re

    lines = raw_text.splitlines()
    rows = []
    pattern = re.compile(
        r"(?P<code>[A-Z]{2,4}\d{3}[A-Z]?)"
        r"\s+(?P<credits>\d+\.?\d*)"
        r"\s+(?P<grade>[A-DF][+-]?|W|I)"
        r"(?:\s+(?P<semester>(?:Spring|Summer|Fall)\s*\d{4}))?",
        re.IGNORECASE,
    )
    attempt_counter: dict[str, int] = {}
    for line in lines:
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
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Course_Code", "Credits", "Grade", "Semester", "Attempt"])
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ── Per-file audit (runs in subprocess pool) ──────────────────────────────────

def _audit_csv_file(args: tuple[str, str, str]) -> dict[str, Any]:
    """Process one CSV file. Called in a subprocess."""
    csv_path, program, file_name = args
    from packages.api.main import _run_audit
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            csv_text = f.read()
        result = _run_audit(csv_text, program)
        return {"file": file_name, "status": "ok", "result": result}
    except Exception as e:
        return {"file": file_name, "status": "error", "error": str(e)}


def _audit_image_file(args: tuple[str, str, str]) -> dict[str, Any]:
    """OCR + audit one image/PDF. Called in a subprocess."""
    img_path, program, file_name = args
    try:
        raw_text = _ocr_image_file(img_path)
        csv_text = _ocr_text_to_csv(raw_text)
        if not csv_text:
            return {"file": file_name, "status": "error", "error": "OCR extracted no courses"}

        from packages.api.main import _run_audit

        result = _run_audit(csv_text, program)
        return {"file": file_name, "status": "ok", "result": result}
    except Exception as e:
        return {"file": file_name, "status": "error", "error": str(e)}

# ── Background job runner ─────────────────────────────────────────────────────

MAX_WORKERS = int(os.environ.get("BATCH_WORKERS", "4"))


def _run_batch_job(job_id: str, task_args: list, mode: str):
    """Run in a background thread. Updates _JOBS[job_id] progress."""
    _JOBS[job_id]["status"]  = "running"
    _JOBS[job_id]["total"]   = len(task_args)
    _JOBS[job_id]["done"]    = 0
    _JOBS[job_id]["results"] = []
    _JOBS[job_id]["errors"]  = []

    fn = _audit_csv_file if mode == "csv" else _audit_image_file

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fn, a): a for a in task_args}
        for future in as_completed(futures):
            out = future.result()
            _JOBS[job_id]["done"] += 1
            if out["status"] == "ok":
                _JOBS[job_id]["results"].append(out)
            else:
                _JOBS[job_id]["errors"].append(out)

    _JOBS[job_id]["status"]   = "done"
    _JOBS[job_id]["finished"] = time.time()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{job_id}")
def get_job(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/csv")
async def batch_csv(
    background_tasks: BackgroundTasks,
    program: str = Form(...),
    zip_file: UploadFile = File(None),
    csvs: list[UploadFile] = File(None),
):
    """
    Upload either:
      - A single ZIP containing CSV files, OR
      - Multiple individual CSV files (up to 20k)
    Runs audits in a background process pool.
    Returns a job_id to poll for progress.
    """
    if not zip_file and not csvs:
        raise HTTPException(status_code=400, detail="Provide zip_file or csvs")

    tmpdir = tempfile.mkdtemp()
    task_args: list[tuple[str, str, str]] = []

    try:
        if zip_file:
            raw = await zip_file.read()
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".csv"):
                        dest = os.path.join(tmpdir, name.replace("/", "_"))
                        zf.extract(name, tmpdir)
                        task_args.append((dest, program, name))
        else:
            for upload in (csvs or []):
                dest = os.path.join(tmpdir, upload.filename or f"{uuid.uuid4()}.csv")
                content = await upload.read()
                Path(dest).write_bytes(content)
                task_args.append((dest, program, upload.filename or dest))

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not task_args:
        raise HTTPException(status_code=400, detail="No CSV files found")

    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"status": "queued", "created": time.time(), "mode": "csv"}
    background_tasks.add_task(_run_batch_job, job_id, task_args, "csv")

    return {"job_id": job_id, "files_queued": len(task_args), "poll": f"/batch/{job_id}"}


@router.post("/images")
async def batch_images(
    background_tasks: BackgroundTasks,
    program: str = Form(...),
    zip_file: UploadFile = File(...),
):
    """
    Upload a ZIP of transcript images/PDFs.
    Uses Tesseract OCR (free, self-hosted) → audit pipeline.
    Poll /batch/{job_id} for progress.
    """
    tmpdir = tempfile.mkdtemp()
    task_args: list[tuple[str, str, str]] = []
    ALLOWED = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"}

    raw = await zip_file.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for name in zf.namelist():
            if Path(name).suffix.lower() in ALLOWED:
                dest = os.path.join(tmpdir, name.replace("/", "_"))
                data = zf.read(name)
                Path(dest).write_bytes(data)
                task_args.append((dest, program, name))

    if not task_args:
        raise HTTPException(status_code=400, detail="No image/PDF files found in ZIP")

    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"status": "queued", "created": time.time(), "mode": "images"}
    background_tasks.add_task(_run_batch_job, job_id, task_args, "images")

    return {
        "job_id":       job_id,
        "files_queued": len(task_args),
        "ocr_engine":   "Tesseract (self-hosted, free, unlimited)",
        "poll":         f"/batch/{job_id}",
        "note":         "Expect ~2-5s per image. 20k images ≈ 14-28 hours with 4 workers.",
    }
