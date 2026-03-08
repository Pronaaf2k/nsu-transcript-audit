"""
runner.py — Thin glue layer that calls the existing audit_l*.py
scripts from the parent CSE226Proj1 project and returns a
structured JSON-serialisable result dict.

It resolves the audit_l*.py files relative to a configurable
AUDIT_SOURCE_DIR env var (defaults to the CSE226Proj1 sibling dir).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Default: sibling folder to this repo
_DEFAULT_SRC = str(Path(__file__).resolve().parents[2] / "CSE226Proj1")


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def run_audit(
    courses: list[dict[str, Any]],
    program: str,
    source_dir: str | None = None,
) -> dict[str, Any]:
    """
    Run the full L1→L2→L3 audit pipeline on a normalised course list.

    Args:
        courses:    Output of parse_csv_transcript()
        program:   e.g. "CSE", "BBA", "EEE"
        source_dir: Path to the directory containing audit_l*.py

    Returns:
        {
          "l1": { credits, cgpa, status },
          "l2": { ... },
          "l3": { deficiencies, warnings, passed },
        }
    """
    src = source_dir or os.environ.get("AUDIT_SOURCE_DIR", _DEFAULT_SRC)

    l1 = _load_module("audit_l1", os.path.join(src, "audit_l1.py"))
    l2 = _load_module("audit_l2", os.path.join(src, "audit_l2.py"))
    l3 = _load_module("audit_l3", os.path.join(src, "audit_l3.py"))

    l1_result = l1.run(courses)
    l2_result = l2.run(courses, l1_result)
    l3_result = l3.run(courses, l1_result, l2_result, program)

    return {
        "l1": l1_result,
        "l2": l2_result,
        "l3": l3_result,
        "program": program,
    }
