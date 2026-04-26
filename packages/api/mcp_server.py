"""
mcp_server.py — MCP (Model Context Protocol) Server for NSU Transcript Audit

This server exposes audit functionality to AI agents via the MCP protocol.
Compatible with Claude Desktop, Cursor, and other MCP clients.

Usage:
    # Claude Desktop (add to claude_desktop_config.json):
    {
        "mcpServers": {
            "nsu-audit": {
                "command": "python",
                "args": ["F:/Github/nsu-transcript-audit/packages/api/mcp_server.py"]
            }
        }
    }
    
    # Cursor AI:
    # Add similar configuration to .cursor/mcp.json
"""

import json
import os
import re
import sys
import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

MCP_VERSION = "2024-11-05"
EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "node_modules",
    "runs",
    "checkpoints",
    "datasets",
    "weights",
    "wandb",
}
DATASET_DIR_HINTS = {"data", "dataset", "datasets", "samples", "fixtures", "annotations"}
TRAINING_DIR_HINTS = {"runs", "checkpoints", "wandb", "tensorboard", "outputs", "logs"}
METRIC_KEYS = {"cer", "wer", "accuracy", "acc", "loss", "f1", "precision", "recall"}
TEXT_LOG_EXTENSIONS = {".log", ".txt", ".out"}
MANIFEST_NAMES = {
    "manifest.json",
    "manifest.jsonl",
    "dataset.json",
    "dataset.jsonl",
    "metadata.json",
    "annotations.json",
}


def jsonrpc_response(result: Any, error: dict | None = None, request_id: int = 1) -> dict:
    if error:
        return {"jsonrpc": "2.0", "id": request_id, "error": error}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error(code: int, message: str, request_id: int = 1) -> dict:
    return jsonrpc_response(None, {"code": code, "message": message}, request_id)


def _safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve()).replace("\\", "/")


def _iter_files(limit: int = 5000) -> Iterator[Path]:
    seen = 0
    for current_root, dirnames, filenames in os.walk(ROOT_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        root_path = Path(current_root)
        for filename in filenames:
            if filename.startswith(".env"):
                continue
            path = root_path / filename
            yield path
            seen += 1
            if seen >= limit:
                return


def _iter_dirs(limit: int = 1000) -> Iterator[Path]:
    seen = 0
    for current_root, dirnames, _filenames in os.walk(ROOT_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for dirname in dirnames:
            path = Path(current_root) / dirname
            yield path
            seen += 1
            if seen >= limit:
                return


def _read_text(path: Path, max_chars: int = 120_000) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def _find_recent_files(candidates: list[Path]) -> list[Path]:
    return sorted((p for p in candidates if p.exists() and p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def _summarize_tree(base: Path, depth: int = 3, max_entries_per_dir: int = 20) -> list[str]:
    lines: list[str] = []

    def walk(path: Path, prefix: str, level: int) -> None:
        if level > depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        visible = [p for p in entries if p.name not in EXCLUDED_DIRS and not p.name.startswith(".env")]
        shown = visible[:max_entries_per_dir]
        for entry in shown:
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{entry.name}{suffix}")
            if entry.is_dir():
                walk(entry, prefix + "  ", level + 1)
        if len(visible) > len(shown):
            lines.append(f"{prefix}... ({len(visible) - len(shown)} more entries)")

    walk(base, "", 1)
    return lines


def _extract_routes_from_source() -> list[dict[str, Any]]:
    main_py = ROOT_DIR / "packages" / "api" / "main.py"
    if not main_py.exists():
        return [{"error": "packages/api/main.py not found"}]

    routes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pattern = re.compile(r'^@app\.(get|post|put|patch|delete)\("([^"]+)"')
    for line in _read_text(main_py, max_chars=200_000).splitlines():
        match = pattern.match(line.strip())
        if match:
            current = {
                "path": match.group(2),
                "methods": [match.group(1).upper()],
                "name": None,
                "source": "source_parse",
            }
            routes.append(current)
            continue
        stripped = line.strip()
        if current and stripped.startswith("def "):
            current["name"] = stripped.split("def ", 1)[1].split("(", 1)[0]
            current = None
    return sorted(routes, key=lambda item: item["path"])


def _extract_routes_from_fastapi() -> list[dict[str, Any]]:
    try:
        from packages.api.main import app

        routes = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = sorted(m for m in (getattr(route, "methods", None) or set()) if m not in {"HEAD", "OPTIONS"})
            if path and methods:
                routes.append({
                    "path": path,
                    "methods": methods,
                    "name": getattr(route, "name", None),
                    "source": "fastapi_import",
                })
        return sorted(routes, key=lambda item: item["path"])
    except Exception:
        return _extract_routes_from_source()


def _scan_dataset_candidates() -> dict[str, Any]:
    dataset_dirs: list[dict[str, Any]] = []
    manifest_files: list[str] = []
    sample_files: list[str] = []

    for path in _iter_files():
        parts = {part.lower() for part in path.parts}
        if path.name.lower() in MANIFEST_NAMES:
            manifest_files.append(_safe_rel(path))
        if path.suffix.lower() in {".csv", ".json", ".jsonl", ".txt"} and (DATASET_DIR_HINTS & parts or path.name.startswith("test_")):
            sample_files.append(_safe_rel(path))

    candidate_dirs: set[Path] = set()
    for item in _iter_dirs():
        if item.name.lower() in DATASET_DIR_HINTS:
            candidate_dirs.add(item)

    for directory in sorted(candidate_dirs):
        file_count = 0
        text_count = 0
        for child in directory.rglob("*"):
            if child.is_file():
                file_count += 1
                if child.suffix.lower() in {".csv", ".json", ".jsonl", ".txt", ".jpg", ".jpeg", ".png", ".pdf"}:
                    text_count += 1
        dataset_dirs.append({
            "name": directory.name,
            "path": _safe_rel(directory),
            "file_count": file_count,
            "recognized_file_count": text_count,
        })

    return {
        "dataset_dirs": dataset_dirs,
        "manifest_files": sorted(manifest_files)[:50],
        "sample_files": sorted(sample_files)[:50],
    }


def _find_training_artifacts() -> dict[str, list[Path]]:
    logs: list[Path] = []
    metrics: list[Path] = []
    checkpoints: list[Path] = []

    for path in _iter_files():
        lower_parts = {part.lower() for part in path.parts}
        lower_name = path.name.lower()
        if path.suffix.lower() in TEXT_LOG_EXTENSIONS and (TRAINING_DIR_HINTS & lower_parts or "train" in lower_name or "eval" in lower_name):
            logs.append(path)
        if path.suffix.lower() in {".json", ".jsonl", ".csv", ".txt"} and any(key in lower_name for key in ["metric", "eval", "result", "report"]):
            metrics.append(path)
        if path.suffix.lower() in {".ckpt", ".pt", ".pth", ".bin", ".safetensors"} or "checkpoint" in lower_name:
            checkpoints.append(path)

    return {
        "logs": _find_recent_files(logs),
        "metrics": _find_recent_files(metrics),
        "checkpoints": _find_recent_files(checkpoints),
    }


def _extract_metrics_from_text(text: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for key in METRIC_KEYS:
        pattern = rf"(?i)\b{re.escape(key)}\b\s*[:=]\s*(-?\d+(?:\.\d+)?)"
        match = re.search(pattern, text)
        if match:
            try:
                results[key] = float(match.group(1))
            except ValueError:
                results[key] = match.group(1)
    return results


def _extract_metrics_from_file(path: Path) -> dict[str, Any]:
    try:
        if path.suffix.lower() in {".json", ".jsonl"}:
            text = _read_text(path)
            if path.suffix.lower() == ".jsonl":
                for line in reversed([line for line in text.splitlines() if line.strip()]):
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    metrics = {k: v for k, v in data.items() if str(k).lower() in METRIC_KEYS}
                    if metrics:
                        return metrics
            data = json.loads(text)
            if isinstance(data, dict):
                direct = {k: v for k, v in data.items() if str(k).lower() in METRIC_KEYS}
                if direct:
                    return direct
                nested = data.get("metrics")
                if isinstance(nested, dict):
                    return {k: v for k, v in nested.items() if str(k).lower() in METRIC_KEYS}
        if path.suffix.lower() == ".csv":
            text = _read_text(path)
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                row = rows[-1]
                return {k: row[k] for k in row if k.lower() in METRIC_KEYS and row[k] not in {"", None}}
        return _extract_metrics_from_text(_read_text(path, max_chars=20_000))
    except Exception as exc:
        return {"error": str(exc)}


def run_audit_from_csv(csv_text: str, program: str = "CSE") -> dict:
    """Run a full audit (L1, L2, L3) on CSV transcript data."""
    import csv
    import io
    
    from packages.core.unified import UnifiedAuditor
    
    reader = csv.DictReader(io.StringIO(csv_text))
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
    
    result = UnifiedAuditor.run_from_rows(rows, program, concentration=None)
    
    eligible = result.get("level_3", {}).get("eligible", False) if result.get("level_3") else False
    total_cr = result.get("level_1", {}).get("credits_earned", 0) if result.get("level_1") else 0
    cgpa = result.get("level_2", {}).get("cgpa", 0.0) if result.get("level_2") else 0.0
    
    return {
        "status": "success",
        "program": program,
        "total_credits": total_cr,
        "cgpa": cgpa,
        "graduation_status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "eligible": eligible,
        "level_1": result.get("level_1", {}),
        "level_2": result.get("level_2", {}),
        "level_3": result.get("level_3", {})
    }


def get_cgpa_breakdown(csv_text: str) -> dict:
    """Get detailed CGPA breakdown by semester."""
    import csv
    import io
    
    GRADE_POINTS = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0}
    
    reader = csv.DictReader(io.StringIO(csv_text))
    reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
    
    semesters = {}
    for r in reader:
        sem = r.get("Semester", "Unknown").strip()
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append({
            "course_code": r.get("Course_Code", "").strip(),
            "credits": float(r.get("Credits", 0) or 0),
            "grade": r.get("Grade", "").strip()
        })
    
    cumulative = {}
    results = []
    
    for sem in sorted(semesters.keys()):
        sem_rows = semesters[sem]
        sem_pts = 0
        sem_cred = 0
        
        for row in sem_rows:
            pts = GRADE_POINTS.get(row["grade"].upper(), None)
            if pts is not None and row["credits"] > 0:
                sem_pts += pts * row["credits"]
                sem_cred += row["credits"]
                
                code = row["course_code"]
                if code not in cumulative:
                    cumulative[code] = {"points": pts, "credits": row["credits"]}
                elif pts > cumulative[code]["points"]:
                    cumulative[code] = {"points": pts, "credits": row["credits"]}
        
        tgpa = int((sem_pts / sem_cred if sem_cred > 0 else 0) * 100) / 100
        total_pts = sum(d["points"] * d["credits"] for d in cumulative.values())
        total_cred = sum(d["credits"] for d in cumulative.values())
        cgpa = int((total_pts / total_cred if total_cred > 0 else 0) * 100) / 100
        
        results.append({
            "semester": sem,
            "tgpa": tgpa,
            "cgpa": cgpa,
            "credits": sem_cred,
            "courses": len(sem_rows)
        })
    
    return {
        "status": "success",
        "semesters": results,
        "final_cgpa": results[-1]["cgpa"] if results else 0,
        "total_credits": sum(s["credits"] for s in results)
    }


def check_missing_courses(csv_text: str, program: str = "CSE") -> dict:
    """Check which required courses are missing for graduation."""
    from packages.cli.audit.audit_l3 import parse_program_knowledge, audit_student
    
    program_file = ROOT_DIR / "packages" / "cli" / "program.md"
    if not program_file.exists():
        program_file = ROOT_DIR / "program.md"
    
    full_name = {
        "CSE": "Computer Science & Engineering",
        "BBA": "Business Administration",
        "ETE": "Electronic & Telecom Engineering",
        "ENV": "Environmental Science & Management",
        "ENG": "English",
        "ECO": "Economics",
    }.get(program.upper(), program)
    
    if not program_file.exists():
        return {"status": "error", "message": "Program file not found"}
    
    requirements = parse_program_knowledge(str(program_file), full_name)
    result = audit_student(csv_text, requirements, md_file=str(program_file))
    
    return {
        "status": "success",
        "program": program,
        "missing": result["missing"],
        "invalid_electives": result["invalid_electives"],
        "advisories": result["advisories"],
        "total_earned": result["total_earned"],
        "required": requirements["total_credits_required"]
    }


def get_audit_history(limit: int = 10) -> dict:
    from packages.api.local_storage import get_audit_history as get_history
    try:
        history = get_history(limit=limit)
        return {"status": "success", "audits": history}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_audit_by_id(audit_id: str) -> dict:
    from packages.api.local_storage import get_audit as get_audit_local
    try:
        audit = get_audit_local(audit_id)
        if not audit:
            return {"status": "error", "message": "Audit not found"}
        return {"status": "success", "audit": audit}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _infer_program_from_csv(csv_text: str) -> tuple[str | None, float]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return None, 0.0

    program_prefixes = {
        "CSE": {"CSE", "MAT", "PHY", "CHE"},
        "BBA": {"ACT", "FIN", "MGT", "MKT", "MIS", "BUS", "ACC"},
        "ETE": {"ETE", "EEE", "PHY", "MAT", "CSE"},
        "ENV": {"ENV", "EVM", "BIO", "CHE"},
        "ENG": {"ENG", "LIN", "LIT"},
        "ECO": {"ECO", "ECN", "MAT"},
    }
    scores = {p: 0 for p in program_prefixes}
    matched = 0

    for row in rows:
        code = str(row.get("Course_Code", "")).strip().upper()
        m = re.match(r"^[A-Z]{3}", code)
        if not m:
            continue
        prefix = m.group(0)
        hit = False
        for prog, prefixes in program_prefixes.items():
            if prefix in prefixes:
                scores[prog] += 1
                hit = True
        if hit:
            matched += 1

    if matched == 0:
        return None, 0.0
    inferred = max(scores, key=scores.get)
    return inferred, scores[inferred] / matched


def ocr_extract_csv(file_path: str) -> dict:
    """Extract transcript CSV from a local PDF/image file using Gemini OCR."""
    from packages.core.pdf_parser import VisionParser

    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return {"status": "error", "message": f"File not found: {file_path}"}

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {"status": "error", "message": "GEMINI_API_KEY is not configured"}

    try:
        file_bytes = p.read_bytes()
        rows = VisionParser.parse(file_bytes, api_key, filename=p.name)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["Course_Code", "Course_Name", "Credits", "Grade", "Semester"])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "Course_Code": r.get("course_code", ""),
                "Course_Name": r.get("course_name", ""),
                "Credits": str(r.get("credits", "")),
                "Grade": r.get("grade", ""),
                "Semester": r.get("semester", ""),
            })
        csv_text = buf.getvalue()
        inferred_program, confidence = _infer_program_from_csv(csv_text)
        return {
            "status": "success",
            "file": str(p),
            "rows_extracted": len(rows),
            "csv_text": csv_text,
            "program_inferred": inferred_program,
            "program_inference_confidence": round(confidence, 3),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def health_check() -> dict:
    result: dict[str, Any] = {"backend_url": BACKEND_URL, "backend_alive": False}
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{BACKEND_URL}/health")
        result["backend_alive"] = response.is_success
        result["status_code"] = response.status_code
        if response.headers.get("content-type", "").startswith("application/json"):
            result["payload"] = response.json()
        else:
            result["payload_preview"] = response.text[:500]
    except Exception as exc:
        result["error"] = str(exc)
    return result


def inspect_project_structure() -> dict:
    return {
        "root": str(ROOT_DIR),
        "excluded_dirs": sorted(EXCLUDED_DIRS),
        "tree": _summarize_tree(ROOT_DIR),
    }


def list_available_routes() -> dict:
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{BACKEND_URL}/openapi.json")
        if response.is_success:
            spec = response.json()
            routes = []
            for path, methods in spec.get("paths", {}).items():
                routes.append({
                    "path": path,
                    "methods": sorted(method.upper() for method in methods.keys()),
                    "source": "openapi",
                })
            return {"source": "openapi", "backend_url": BACKEND_URL, "routes": sorted(routes, key=lambda item: item["path"])}
    except Exception:
        pass

    routes = _extract_routes_from_fastapi()
    source = "fastapi_import"
    if routes and all(route.get("source") == "source_parse" for route in routes if isinstance(route, dict) and "path" in route):
        source = "source_parse"
    return {"source": source, "routes": routes}


def list_datasets() -> dict:
    scan = _scan_dataset_candidates()
    return {
        "dataset_dirs": scan["dataset_dirs"],
        "manifest_files": scan["manifest_files"],
        "sample_files": scan["sample_files"],
        "note": "This repo appears to be an OCR/audit app. Results may mostly be fixtures or sample CSVs rather than training datasets.",
    }


def get_training_status() -> dict:
    artifacts = _find_training_artifacts()
    latest_log = artifacts["logs"][0] if artifacts["logs"] else None
    latest_metric = artifacts["metrics"][0] if artifacts["metrics"] else None
    latest_checkpoint = artifacts["checkpoints"][0] if artifacts["checkpoints"] else None
    return {
        "has_training_artifacts": bool(latest_log or latest_metric or latest_checkpoint),
        "latest_log": _safe_rel(latest_log) if latest_log else None,
        "latest_metrics": _safe_rel(latest_metric) if latest_metric else None,
        "latest_checkpoint": _safe_rel(latest_checkpoint) if latest_checkpoint else None,
        "log_count": len(artifacts["logs"]),
        "metrics_count": len(artifacts["metrics"]),
        "checkpoint_count": len(artifacts["checkpoints"]),
        "note": "No long-running jobs are started by this tool. It only inspects existing files.",
    }


def read_recent_training_log(lines: int = 100) -> dict:
    safe_lines = max(1, min(int(lines), 200))
    artifacts = _find_training_artifacts()
    if not artifacts["logs"]:
        return {
            "status": "not_available",
            "message": "No likely training or evaluation log files were found in the repository.",
        }
    log_path = artifacts["logs"][0]
    text = _read_text(log_path, max_chars=80_000)
    tail = "\n".join(text.splitlines()[-safe_lines:])
    return {
        "status": "ok",
        "path": _safe_rel(log_path),
        "lines_requested": safe_lines,
        "content": tail[:12_000],
    }


def run_ocr_on_image_path(image_path: str) -> dict:
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = (ROOT_DIR / candidate).resolve()
    return ocr_extract_csv(str(candidate))


def get_latest_eval_metrics() -> dict:
    artifacts = _find_training_artifacts()
    if not artifacts["metrics"]:
        return {
            "status": "not_available",
            "message": "No metrics or evaluation files were found.",
        }
    metric_path = artifacts["metrics"][0]
    metrics = _extract_metrics_from_file(metric_path)
    return {
        "status": "ok" if metrics and "error" not in metrics else "not_available",
        "path": _safe_rel(metric_path),
        "metrics": metrics,
    }


TOOLS = {
    "health_check": {
        "description": "Check whether the configured backend is alive",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "inspect_project_structure": {
        "description": "Return a summarized project tree excluding large and sensitive folders",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "list_available_routes": {
        "description": "List backend routes from OpenAPI when available, or source inspection otherwise",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "list_datasets": {
        "description": "Search for dataset-like folders, manifests, and sample files",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "get_training_status": {
        "description": "Inspect the repo for training logs, metrics, and checkpoint artifacts",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "read_recent_training_log": {
        "description": "Read the tail of the most relevant training or evaluation log file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lines": {"type": "number", "description": "Maximum lines to return", "default": 100}
            }
        }
    },
    "run_ocr_on_image_path": {
        "description": "Run OCR on a local image or PDF path using the existing project OCR parser",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Absolute or repo-relative path to an image or PDF"}
            },
            "required": ["image_path"]
        }
    },
    "get_latest_eval_metrics": {
        "description": "Return the latest evaluation metrics found in the repository",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "audit_run": {
        "description": "Run a full L1/L2/L3 audit on a CSV transcript",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"},
                "program": {"type": "string", "description": "Program code (CSE, BBA, ETE, ENV, ENG, ECO)", "default": "CSE"}
            },
            "required": ["csv_text"]
        }
    },
    "cgpa_breakdown": {
        "description": "Get semester-by-semester CGPA breakdown",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"}
            },
            "required": ["csv_text"]
        }
    },
    "check_missing": {
        "description": "Check which required courses are missing for graduation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"},
                "program": {"type": "string", "description": "Program code (CSE, BBA, ETE, ENV, ENG, ECO)", "default": "CSE"}
            },
            "required": ["csv_text"]
        }
    },
    "history_list": {
        "description": "Get recent audit history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "description": "Maximum number of results", "default": 10}
            }
        }
    },
    "history_get": {
        "description": "Get a specific audit by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "audit_id": {"type": "string", "description": "The audit ID to retrieve"}
            },
            "required": ["audit_id"]
        }
    },
    "ocr_extract": {
        "description": "Extract CSV from a local transcript image/PDF using OCR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to transcript file (.pdf/.png/.jpg/.jpeg/.webp)"}
            },
            "required": ["file_path"]
        }
    }
}


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    if tool_name == "health_check":
        return health_check()
    elif tool_name == "inspect_project_structure":
        return inspect_project_structure()
    elif tool_name == "list_available_routes":
        return list_available_routes()
    elif tool_name == "list_datasets":
        return list_datasets()
    elif tool_name == "get_training_status":
        return get_training_status()
    elif tool_name == "read_recent_training_log":
        return read_recent_training_log(arguments.get("lines", 100))
    elif tool_name == "run_ocr_on_image_path":
        return run_ocr_on_image_path(arguments["image_path"])
    elif tool_name == "get_latest_eval_metrics":
        return get_latest_eval_metrics()
    elif tool_name == "audit_run":
        return run_audit_from_csv(arguments["csv_text"], arguments.get("program", "CSE"))
    elif tool_name == "cgpa_breakdown":
        return get_cgpa_breakdown(arguments["csv_text"])
    elif tool_name == "check_missing":
        return check_missing_courses(arguments["csv_text"], arguments.get("program", "CSE"))
    elif tool_name == "history_list":
        return get_audit_history(arguments.get("limit", 10))
    elif tool_name == "history_get":
        return get_audit_by_id(arguments["audit_id"])
    elif tool_name == "ocr_extract":
        return ocr_extract_csv(arguments["file_path"])
    else:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 1)
    
    if method == "initialize":
        return jsonrpc_response({
            "protocolVersion": MCP_VERSION,
            "serverInfo": {"name": "nsu-audit", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": True}}
        }, request_id=request_id)
    
    elif method == "tools/list":
        tools_list = []
        for name, spec in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return jsonrpc_response({"tools": tools_list}, request_id=request_id)
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in TOOLS:
            return jsonrpc_error(-32601, f"Unknown tool: {tool_name}", request_id)
        
        try:
            result = handle_tool_call(tool_name, arguments)
            return jsonrpc_response({
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            }, request_id=request_id)
        except Exception as e:
            return jsonrpc_error(-32603, f"Tool error: {str(e)}", request_id)
    
    elif method == "ping":
        return jsonrpc_response({"pong": True}, request_id=request_id)
    
    else:
        return jsonrpc_error(-32601, f"Method not found: {method}", request_id)


def main():
    print("NSU Audit MCP Server starting...", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps(jsonrpc_error(-32700, f"Parse error: {str(e)}")), flush=True)
        except Exception as e:
            print(json.dumps(jsonrpc_error(-32603, f"Server error: {str(e)}")), flush=True)


if __name__ == "__main__":
    main()
