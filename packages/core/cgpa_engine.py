"""
GradeTrace Core — CGPA Auditor (Level 2)

Computes CGPA, academic standing, probation history, and waiver logic.

Ported from engine/cgpa_engine.py — algorithms unchanged.
"""

import copy

from packages.core.models import (
    CourseRecord, SEMESTERS, GPA_EXCLUDED_GRADES, grade_to_points,
)


class CGPAAuditor:
    """Level 2 — CGPA Calculation & Standing Engine."""

    # ───────────────────────────────────────────────
    # CGPA Computation
    # ───────────────────────────────────────────────

    @staticmethod
    def compute_cgpa(records: list[CourseRecord]) -> tuple[float, float, int]:
        """
        Compute CGPA using only BEST-grade attempts.
        - Excludes W, T grades entirely
        - Excludes 0-credit courses
        - I (Incomplete) treated as F (0.0)
        - Only BEST or standalone FAILED attempts count

        Returns (cgpa, total_quality_points, total_gpa_credits).
        """
        total_qp = 0.0
        total_gc = 0

        for r in records:
            if r.status not in ("BEST", "FAILED"):
                continue
            if r.credits == 0:
                continue
            points = grade_to_points(r.grade)
            if points is None:
                continue
            total_qp += points * r.credits
            total_gc += r.credits

        if total_gc == 0:
            return 0.0, 0.0, 0

        cgpa = total_qp / total_gc
        # NSU truncation: 1.996 → 1.99 (never round up)
        truncated = int(cgpa * 100) / 100.0
        return truncated, round(total_qp, 2), total_gc

    @staticmethod
    def compute_major_cgpa(records: list[CourseRecord], major_course_codes: list[str]) -> float:
        """Compute CGPA for only the specified major/core courses."""
        major_codes = set(major_course_codes)
        total_qp = 0.0
        total_cr = 0

        for r in records:
            if r.course_code not in major_codes:
                continue
            if r.status not in ("BEST", "FAILED"):
                continue
            if r.credits == 0:
                continue
            points = grade_to_points(r.grade)
            if points is None:
                continue
            total_qp += points * r.credits
            total_cr += r.credits

        if total_cr == 0:
            return 0.0
        return int((total_qp / total_cr) * 100) / 100.0

    # ───────────────────────────────────────────────
    # Academic Standing
    # ───────────────────────────────────────────────

    @staticmethod
    def determine_standing(cgpa: float) -> str:
        """Determine academic standing based on overall CGPA."""
        if cgpa < 2.0:
            return "PROBATION"
        return "NORMAL"

    @staticmethod
    def calculate_probation_history(records: list[CourseRecord]) -> tuple[str, int]:
        """
        Calculate probation phase based on consecutive semesters < 2.0 CGPA.
        NSU Policy: 2 consecutive semesters allowed; dismissal on the 3rd.

        Returns (standing_label, consecutive_count).
        """
        from packages.core.credit_engine import CreditAuditor

        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}
        transcript_sems = sorted(
            list(set(r.semester for r in records if r.semester in sem_map)),
            key=lambda s: sem_map[s],
        )

        if not transcript_sems:
            return "NORMAL", 0

        consecutive_p = 0
        for current_sem in transcript_sems:
            cutoff_idx = sem_map[current_sem]
            subset = [copy.copy(r) for r in records
                      if r.semester in sem_map and sem_map[r.semester] <= cutoff_idx]
            resolved = CreditAuditor.resolve_retakes(subset)
            snap_cgpa, _, _ = CGPAAuditor.compute_cgpa(resolved)

            if snap_cgpa < 2.0:
                consecutive_p += 1
            else:
                consecutive_p = 0

        if consecutive_p == 0:
            return "NORMAL", 0
        elif consecutive_p == 1:
            return "PROBATION (P1)", 1
        elif consecutive_p == 2:
            return "PROBATION (P2)", 2
        else:
            return "DISMISSAL", consecutive_p

    # ───────────────────────────────────────────────
    # Waiver Logic
    # ───────────────────────────────────────────────

    @staticmethod
    def check_waivers(program: str, records: list[CourseRecord],
                      user_waivers: dict | None = None) -> tuple[dict, int]:
        """
        Check waiver eligibility.

        If user_waivers is provided (e.g. {"ENG102": True}), use those.
        Otherwise scan transcript for T-grade waivers.

        Returns (waivers_dict, credit_reduction).
        """
        if user_waivers is not None:
            return CGPAAuditor._check_waivers_from_input(program, user_waivers)

        if program.upper() == "CSE":
            return CGPAAuditor._check_waivers_cse(records)
        return CGPAAuditor._check_waivers_bba(records)

    @staticmethod
    def _check_waivers_cse(records: list[CourseRecord]) -> tuple[dict, int]:
        waivers = {"ENG102": False}
        credit_reduction = 0
        for r in records:
            if r.course_code == "ENG102":
                if r.grade == "T":
                    waivers["ENG102"] = True
                    credit_reduction += 3
                elif r.status in ("BEST", "WAIVED") and r.grade not in ("F", "I", "W"):
                    waivers["ENG102"] = True
        return waivers, credit_reduction

    @staticmethod
    def _check_waivers_bba(records: list[CourseRecord]) -> tuple[dict, int]:
        waivers = {"ENG102": False, "BUS112": False}
        credit_reduction = 0
        for r in records:
            if r.course_code == "ENG102":
                if r.grade == "T":
                    waivers["ENG102"] = True
                    credit_reduction += 3
                elif r.status in ("BEST", "WAIVED") and r.grade not in ("F", "I", "W"):
                    waivers["ENG102"] = True
            if r.course_code == "BUS112":
                if r.grade == "T":
                    waivers["BUS112"] = True
                    credit_reduction += 3
                elif r.status in ("BEST",) and r.grade not in ("F", "I", "W"):
                    waivers["BUS112"] = True
        return waivers, credit_reduction

    @staticmethod
    def _check_waivers_from_input(program: str, user_waivers: dict) -> tuple[dict, int]:
        credit_reduction = 0
        if program.upper() == "CSE":
            if user_waivers.get("ENG102", False):
                credit_reduction += 3
        else:
            if user_waivers.get("ENG102", False):
                credit_reduction += 3
            if user_waivers.get("BUS112", False):
                credit_reduction += 3
        return user_waivers, credit_reduction

    # ───────────────────────────────────────────────
    # Full Level 2 Pipeline
    # ───────────────────────────────────────────────

    @staticmethod
    def process(records: list[CourseRecord], program: str = "CSE",
                user_waivers: dict | None = None) -> dict:
        """
        Full Level 2 pipeline.

        Returns dict:
            cgpa, quality_points, gpa_credits, standing,
            probation_count, waivers, credit_reduction
        """
        cgpa, qp, gc = CGPAAuditor.compute_cgpa(records)
        standing, p_count = CGPAAuditor.calculate_probation_history(records)
        waivers, credit_reduction = CGPAAuditor.check_waivers(program, records, user_waivers)

        return {
            "cgpa": cgpa,
            "quality_points": qp,
            "gpa_credits": gc,
            "standing": standing,
            "probation_count": p_count,
            "waivers": waivers,
            "credit_reduction": credit_reduction,
        }
