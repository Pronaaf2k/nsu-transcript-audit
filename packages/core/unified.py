"""
GradeTrace Core — Unified Auditor

Runs the full audit pipeline (Level 1 → Level 2 → Level 3 → Roadmap)
and returns a combined report.

This is the primary entry point for the API, CLI, and mobile apps.
"""

import os
import csv
import io
import sys
from pathlib import Path

# Add CLI audit module to path
CLI_AUDIT = Path(__file__).parent.parent / "cli"
sys.path.insert(0, str(CLI_AUDIT))

from packages.core.models import CourseRecord
from packages.core.credit_engine import CreditAuditor
from packages.core.cgpa_engine import CGPAAuditor
from packages.core.audit_engine import GraduationAuditor
from packages.core.course_catalog import CourseCatalog
from packages.core.pdf_parser import VisionParser

# Import CLI audit modules for program.md based validation
try:
    from audit.audit_l3 import parse_program_knowledge, audit_student
    HAS_CLI_AUDIT = True
except ImportError:
    HAS_CLI_AUDIT = False


PROGRAM_MAP = {
    "CSE": "Computer Science & Engineering",
    "BBA": "Business Administration",
    "ETE": "Electronic & Telecom Engineering",
    "ENV": "Environmental Science & Management",
    "ENG": "English",
    "ECO": "Economics",
}

GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}


class UnifiedAuditor:
    """Runs all three audit levels and produces a combined report + roadmap."""

    @staticmethod
    def run_from_file(filepath: str, program: str,
                      concentration: str | None = None,
                      user_waivers: dict | None = None) -> dict:
        """
        Full audit pipeline from a file path (CSV, PDF, or Image).
        """
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        
        if ext in ("pdf", "jpg", "jpeg", "png", "webp"):
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is required for PDF/Image parsing.")
            
            with open(filepath, "rb") as f:
                file_bytes = f.read()
            
            rows = VisionParser.parse(file_bytes, api_key, filename=filepath)
            return UnifiedAuditor.run_from_rows(rows, program, concentration, user_waivers)
            
        level_1 = CreditAuditor.process(filepath)
        records = level_1["records"]
        credits_earned = level_1["credits_earned"]

        if level_1["unrecognized"]:
            return {
                "meta": {
                    "program": program.upper(),
                    "concentration": concentration,
                    "fake_transcript": False,  # Don't fail on unrecognized - may be valid electives
                    "unrecognized_courses": list(level_1["unrecognized"]),
                },
                "level_1": {
                    "credits_attempted": level_1["credits_attempted"],
                    "credits_earned": credits_earned,
                },
                "level_2": None,
                "level_3": None,
                "roadmap": None,
            }

        return UnifiedAuditor._run_pipeline(
            records, program, credits_earned,
            level_1["credits_attempted"], concentration, user_waivers,
        )

    @staticmethod
    def run_from_rows(rows: list[dict], program: str,
                      concentration: str | None = None,
                      user_waivers: dict | None = None) -> dict:
        """
        Full audit pipeline from pre-parsed dict rows (API/DB path).
        Uses program.md for validation instead of hardcoded catalog.
        """
        # Use CLI audit module if available (uses program.md)
        if HAS_CLI_AUDIT:
            return UnifiedAuditor._run_cli_audit(rows, program, concentration)
        
        # Fallback to old behavior
        level_1 = CreditAuditor.process_rows(rows)
        records = level_1["records"]
        credits_earned = level_1["credits_earned"]

        if level_1["unrecognized"]:
            return {
                "meta": {
                    "program": program.upper(),
                    "concentration": concentration,
                    "fake_transcript": False,
                    "unrecognized_courses": list(level_1["unrecognized"]),
                },
                "level_1": {
                    "credits_attempted": level_1["credits_attempted"],
                    "credits_earned": credits_earned,
                },
                "level_2": None,
                "level_3": None,
                "roadmap": None,
            }

        return UnifiedAuditor._run_pipeline(
            records, program, credits_earned,
            level_1["credits_attempted"], concentration, user_waivers,
        )

    @staticmethod
    def _run_cli_audit(rows: list[dict], program: str, concentration: str | None = None) -> dict:
        """
        Use CLI audit modules (program.md based) for L1/L2/L3 audit.
        This validates against the comprehensive program.md instead of hardcoded catalog.
        """
        import tempfile
        
        # Write rows to temp CSV for CLI audit
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['Course_Code', 'Course_Name', 'Credits', 'Grade', 'Semester'])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'Course_Code': row.get('course_code', ''),
                'Course_Name': row.get('course_name', ''),
                'Credits': row.get('credits', 0),
                'Grade': row.get('grade', ''),
                'Semester': row.get('semester', '')
            })
        
        csv_text = csv_content.getvalue()
        
        # Find program.md
        program_file = Path(__file__).parent.parent / "cli" / "program.md"
        if not program_file.exists():
            program_file = Path(__file__).parent.parent.parent / "program.md"
        
        if not program_file.exists():
            return {
                "meta": {
                    "program": program.upper(),
                    "concentration": concentration,
                    "fake_transcript": False,
                    "unrecognized_courses": [],
                },
                "level_1": None,
                "level_2": None,
                "level_3": None,
                "roadmap": None,
                "error": "program.md not found"
            }
        
        full_name = PROGRAM_MAP.get(program.upper(), program)
        
        try:
            requirements = parse_program_knowledge(str(program_file), full_name)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                f.write(csv_text)
                temp_path = f.name
            
            try:
                audit_result = audit_student(temp_path, requirements, md_file=str(program_file))
            finally:
                os.unlink(temp_path)
            
            # Calculate L2 CGPA from rows
            semesters = {}
            for row in rows:
                sem = row.get('semester', 'Unknown')
                if sem not in semesters:
                    semesters[sem] = []
                semesters[sem].append(row)
            
            sorted_sems = sorted(semesters.keys(), key=lambda s: (int(s[-4:]) if s[-4:].isdigit() else 9999, ['Spring', 'Summer', 'Fall'].index(s.split()[0]) if len(s.split()) == 2 and s.split()[0] in ['Spring', 'Summer', 'Fall'] else 99))
            
            cumulative = {}
            semester_results = []
            
            for sem in sorted_sems:
                sem_pts = 0
                sem_cred = 0
                for row in semesters[sem]:
                    grade = row.get('grade', '').upper()
                    credits = float(row.get('credits', 0))
                    pts = GRADE_POINTS.get(grade)
                    
                    if pts is not None and credits > 0 and grade != 'T' and grade not in ('W', 'I', 'F'):
                        sem_pts += pts * credits
                        sem_cred += credits
                        
                        code = row.get('course_code', '')
                        if code not in cumulative or pts > cumulative[code]['points']:
                            cumulative[code] = {'points': pts, 'credits': credits}
                
                tgpa = int((sem_pts / sem_cred if sem_cred > 0 else 0) * 100) / 100
                total_pts = sum(d['points'] * d['credits'] for d in cumulative.values())
                total_cred = sum(d['credits'] for d in cumulative.values())
                cgpa = int((total_pts / total_cred if total_cred > 0 else 0) * 100) / 100
                
                semester_results.append({
                    'semester': sem,
                    'tgpa': tgpa,
                    'cgpa': cgpa,
                    'credits': sem_cred
                })
            
            final_cgpa = semester_results[-1]['cgpa'] if semester_results else 0
            final_cred = sum(d['credits'] for d in cumulative.values())
            
            # Determine standing
            prob_count = 0
            for sem_data in semester_results:
                if sem_data['cgpa'] < 2.0:
                    prob_count += 1
                else:
                    prob_count = 0
            
            standing = 'PROBATION' if prob_count > 0 else 'NORMAL'
            
            return {
                "meta": {
                    "program": program.upper(),
                    "concentration": concentration,
                    "fake_transcript": False,
                    "unrecognized_courses": audit_result.get('invalid_electives', []),
                },
                "level_1": {
                    "credits_attempted": sum(float(r.get('credits', 0)) for r in rows),
                    "credits_earned": audit_result.get('total_earned', 0),
                },
                "level_2": {
                    "cgpa": final_cgpa,
                    "gpa_credits": final_cred,
                    "standing": standing,
                    "probation_count": prob_count,
                    "semesters": semester_results,
                },
                "level_3": {
                    "eligible": audit_result.get('total_earned', 0) >= requirements['total_credits_required'] and final_cgpa >= requirements['min_cgpa'] and not any(len(m) > 0 for m in audit_result.get('missing', {}).values()),
                    "reasons": [],
                    "missing": audit_result.get('missing', {}),
                    "advisories": audit_result.get('advisories', []),
                    "total_credits_required": requirements['total_credits_required'],
                    "cgpa_required": requirements['min_cgpa'],
                },
                "roadmap": None,
            }
            
        except Exception as e:
            return {
                "meta": {
                    "program": program.upper(),
                    "concentration": concentration,
                    "fake_transcript": False,
                    "unrecognized_courses": [],
                    "error": str(e)
                },
                "level_1": None,
                "level_2": None,
                "level_3": None,
                "roadmap": None,
            }

    @staticmethod
    def _run_pipeline(records: list[CourseRecord], program: str,
                      credits_earned: int, credits_attempted: int,
                      concentration: str | None = None,
                      user_waivers: dict | None = None) -> dict:
        """Internal: run Level 2 + Level 3 + Roadmap on resolved records."""
        program = program.upper()

        # Auto-detect BBA concentration from records if not specified
        if program == "BBA" and concentration is None:
            concentration = UnifiedAuditor._detect_concentration(records)

        # Level 2: CGPA + standing
        cgpa_data = CGPAAuditor.process(records, program, user_waivers)

        # Level 3: Graduation audit
        audit_result = GraduationAuditor.audit(
            records, program,
            cgpa_data["waivers"],
            credits_earned,
            cgpa_data["cgpa"],
            cgpa_data.get("credit_reduction", 0),
            concentration=concentration,
        )

        # Roadmap
        if program == "CSE":
            major_cgpa = audit_result.get("major_core_cgpa", 0.0)
        else:
            major_cgpa = audit_result.get("core_cgpa", 0.0)

        roadmap = GraduationAuditor.build_graduation_roadmap(
            program, records, credits_earned,
            cgpa_data["cgpa"], major_cgpa,
            audit_result, cgpa_data["standing"],
        )

        # Serialize records for JSON output
        records_serialized = [r.to_dict() for r in records]

        return {
            "meta": {
                "program": program,
                "concentration": concentration,
                "fake_transcript": False,
                "unrecognized_courses": [],
            },
            "level_1": {
                "credits_attempted": credits_attempted,
                "credits_earned": credits_earned,
                "records": records_serialized,
            },
            "level_2": {
                "cgpa": cgpa_data["cgpa"],
                "quality_points": cgpa_data["quality_points"],
                "gpa_credits": cgpa_data["gpa_credits"],
                "standing": cgpa_data["standing"],
                "probation_count": cgpa_data["probation_count"],
                "waivers": cgpa_data["waivers"],
                "credit_reduction": cgpa_data["credit_reduction"],
            },
            "level_3": {
                "eligible": audit_result["eligible"],
                "reasons": audit_result["reasons"],
                "remaining": audit_result.get("remaining", {}),
                "total_credits_required": audit_result["total_credits_required"],
                "prereq_violations": audit_result.get("prereq_violations", []),
                # Program-specific CGPAs
                **({"major_core_cgpa": audit_result.get("major_core_cgpa", 0.0),
                    "major_elective_cgpa": audit_result.get("major_elective_cgpa", 0.0)}
                   if program == "CSE" else
                   {"core_cgpa": audit_result.get("core_cgpa", 0.0),
                    "concentration_cgpa": audit_result.get("concentration_cgpa", 0.0),
                    "concentration_label": audit_result.get("concentration_label", "Undeclared")}),
            },
            "roadmap": roadmap,
        }

    @staticmethod
    def _detect_concentration(records: list[CourseRecord]) -> str | None:
        """Attempt to detect BBA concentration from course codes in transcript."""
        passed_codes = {r.course_code for r in records
                        if r.status in ("BEST", "WAIVED") and r.grade not in ("F", "I", "W")}
        best_match = None
        best_count = 0
        for code, (req, elec, label) in CourseCatalog.BBA_CONCENTRATIONS.items():
            all_conc = set(req.keys()) | set(elec.keys())
            count = len(passed_codes & all_conc)
            if count > best_count:
                best_count = count
                best_match = code
        return best_match if best_count >= 2 else None
