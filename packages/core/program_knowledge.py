from __future__ import annotations

import re
from pathlib import Path

from packages.cli.audit.audit_l3 import parse_program_knowledge


PROGRAM_CODE_TO_NAME: dict[str, str] = {
    "CSE": "Computer Science & Engineering",
    "BBA": "Business Administration",
    "BBA-OLD": "Business Administration (Legacy pre-2014)",
    "ETE": "Electronic & Telecom Engineering",
    "ENV": "Environmental Science & Management",
    "ENG": "English",
    "ECO": "Economics",
}

PROGRAM_ALIASES: dict[str, str] = {
    "EEE": "ETE",
    "ECE": "ETE",
    "BBAOLD": "BBA-OLD",
    "BBA_OLD": "BBA-OLD",
    "OLD-BBA": "BBA-OLD",
}


def get_program_md_path() -> Path:
    candidates = [
        Path(__file__).resolve().parents[1] / "cli" / "program.md",
        Path(__file__).resolve().parents[2] / "program.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def normalize_program_code(program: str) -> str:
    code = (program or "").strip().upper()
    if code in PROGRAM_ALIASES:
        return PROGRAM_ALIASES[code]
    return code


def get_program_name(program: str) -> str:
    code = normalize_program_code(program)
    if code == "BBA-OLD":
        # program.md section name remains Business Administration
        return "Business Administration"
    if code in PROGRAM_CODE_TO_NAME:
        return PROGRAM_CODE_TO_NAME[code]

    for value in PROGRAM_CODE_TO_NAME.values():
        if value.lower() == (program or "").strip().lower():
            return value
    return (program or "").strip()


def list_program_names_in_md(md_path: Path | None = None) -> list[str]:
    path = md_path or get_program_md_path()
    if not path.exists():
        return []

    names: list[str] = []
    pattern = re.compile(r"^## \[Program: (.*)\]")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line.strip())
        if match:
            names.append(match.group(1).strip())
    return names


def list_supported_programs() -> list[dict[str, str]]:
    md_names = set(list_program_names_in_md())
    programs: list[dict[str, str]] = []
    for code, name in PROGRAM_CODE_TO_NAME.items():
        if code == "BBA-OLD":
            if (not md_names) or ("Business Administration" in md_names):
                programs.append({"code": code, "name": name})
            continue
        if not md_names or name in md_names:
            programs.append({"code": code, "name": name})
    return programs


def get_program_requirements(program: str) -> dict:
    md_path = get_program_md_path()
    if not md_path.exists():
        raise FileNotFoundError(f"program.md not found at {md_path}")

    program_name = get_program_name(program)
    available = set(list_program_names_in_md(md_path))
    if available and program_name not in available:
        raise ValueError(f"Program not found in program.md: {program}")

    req = parse_program_knowledge(str(md_path), program_name)
    return {
        "program": normalize_program_code(program),
        "program_name": program_name,
        "source": str(md_path),
        "total_credits_required": req.get("total_credits_required", 0),
        "min_cgpa": req.get("min_cgpa", 2.0),
        "major_declaration_credits": req.get("major_declaration_credits", 0),
        "elective_cap": req.get("elective_cap", 0),
        "mandatory_ged": req.get("mandatory_ged", []),
        "core_math": req.get("core_math", []),
        "major_core": req.get("major_core", []),
        "core_business": req.get("core_business", []),
        "core_science": req.get("core_science", []),
        "prerequisites": req.get("prerequisites", {}),
    }
