from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

mcp = FastMCP("project-local-mcp")

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


def _safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve()).replace("\\", "/")


def _iter_files(limit: int = 5000):
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


def _iter_dirs(limit: int = 1000):
    seen = 0
    for current_root, dirnames, _filenames in os.walk(ROOT_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for dirname in dirnames:
            path = Path(current_root) / dirname
            yield path
            seen += 1
            if seen >= limit:
                return


def _is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_LOG_EXTENSIONS | {".json", ".jsonl", ".csv", ".md", ".yaml", ".yml"}:
        return True
    try:
        with path.open("rb") as handle:
            chunk = handle.read(512)
        return b"\x00" not in chunk
    except OSError:
        return False


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
                })
        return sorted(routes, key=lambda item: item["path"])
    except Exception:
        return _extract_routes_from_source()


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


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check whether the configured backend appears to be alive."""
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
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result


@mcp.tool()
def inspect_project_structure() -> dict[str, Any]:
    """Return a summarized project tree while skipping large or sensitive folders."""
    return {
        "root": str(ROOT_DIR),
        "excluded_dirs": sorted(EXCLUDED_DIRS),
        "tree": _summarize_tree(ROOT_DIR),
    }


@mcp.tool()
def list_available_routes() -> dict[str, Any]:
    """List likely backend routes from OpenAPI when available, otherwise import FastAPI routes locally."""
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
                })
            return {"source": "openapi", "backend_url": BACKEND_URL, "routes": sorted(routes, key=lambda item: item["path"])}
    except Exception:
        pass
    routes = _extract_routes_from_fastapi()
    source = "fastapi_import"
    if routes and all(route.get("source") == "source_parse" for route in routes if isinstance(route, dict) and "path" in route):
        source = "source_parse"
    return {"source": source, "routes": routes}


@mcp.tool()
def list_datasets() -> dict[str, Any]:
    """Search the repo for dataset-like folders, manifests, and sample files."""
    scan = _scan_dataset_candidates()
    return {
        "dataset_dirs": scan["dataset_dirs"],
        "manifest_files": scan["manifest_files"],
        "sample_files": scan["sample_files"],
        "note": "This repo appears to be an OCR/audit app. Results may mostly be fixtures or sample CSVs rather than training datasets.",
    }


@mcp.tool()
def get_training_status() -> dict[str, Any]:
    """Inspect the repo for training logs, metrics, and checkpoint artifacts."""
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


@mcp.tool()
def read_recent_training_log(lines: int = 100) -> dict[str, Any]:
    """Read the tail of the most relevant log file, with bounded output."""
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


@mcp.tool()
def run_ocr_on_image_path(image_path: str) -> dict[str, Any]:
    """Run OCR using the project's existing local OCR parser when possible."""
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = (ROOT_DIR / candidate).resolve()
    if not candidate.exists() or not candidate.is_file():
        return {"status": "error", "message": f"File not found: {candidate}"}

    try:
        from packages.core.pdf_parser import VisionParser
    except Exception as exc:
        return {
            "status": "not_implemented",
            "message": "The project OCR parser could not be imported.",
            "details": str(exc),
        }

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "status": "not_implemented",
            "message": "GEMINI_API_KEY is not configured, so local OCR cannot run.",
        }

    try:
        rows = VisionParser.parse(candidate.read_bytes(), api_key, filename=candidate.name)
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["Course_Code", "Course_Name", "Credits", "Grade", "Semester"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "Course_Code": row.get("course_code", ""),
                "Course_Name": row.get("course_name", ""),
                "Credits": row.get("credits", ""),
                "Grade": row.get("grade", ""),
                "Semester": row.get("semester", ""),
            })
        return {
            "status": "success",
            "path": _safe_rel(candidate),
            "rows_extracted": len(rows),
            "csv_text": csv_buffer.getvalue()[:20_000],
            "source": "packages.core.pdf_parser.VisionParser",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def get_latest_eval_metrics() -> dict[str, Any]:
    """Return the latest evaluation or metrics values if the repo contains them."""
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


if __name__ == "__main__":
    mcp.run()
