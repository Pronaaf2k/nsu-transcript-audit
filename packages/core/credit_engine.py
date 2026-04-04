"""
GradeTrace Core — Credit Auditor (Level 1)

Resolves retakes, calculates credits attempted/earned,
detects fake transcripts, and checks for academic dismissal.

Ported from engine/credit_engine.py — algorithms unchanged.
"""

import re
import copy
from collections import defaultdict

from packages.core.models import (
    CourseRecord, PASSING_GRADES, GRADE_ORDER, SEMESTERS, grade_rank,
)
from packages.core.course_catalog import ALL_COURSES
from packages.core.transcript_parser import TranscriptParser


class CreditAuditor:
    """Level 1 — Credit Tallying Engine."""

    CAPSTONES = {"CSE499A", "CSE499B", "BUS498"}

    # ───────────────────────────────────────────────
    # Retake Resolution
    # ───────────────────────────────────────────────

    @staticmethod
    def resolve_retakes(records: list[CourseRecord]) -> list[CourseRecord]:
        """
        Group records by course_code, pick the BEST attempt for each course,
        and assign status labels to every record.

        Status values:
          BEST                — the attempt that counts for credit/GPA
          RETAKE-IGNORED      — a retake superseded by a better grade
          UNAUTHORIZED-RETAKE — retaking a course already passed with >= B-
          WAIVED              — grade is T (transfer/waived)
          WITHDRAWN           — grade is W
          FAILED              — grade is F or I and no better attempt exists
          REJECTED-TRANSFER   — T grade on a non-transferable course
        """
        groups = defaultdict(list)
        for r in records:
            groups[r.course_code].append(r)

        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}
        current_semester_index = len(SEMESTERS)

        for code, attempts in groups.items():
            attempts.sort(key=lambda a: sem_map.get(a.semester, -1))

            passed_with_b_minus = False
            for rec in attempts:
                # Incomplete timer expired → convert to F
                if rec.grade == "I":
                    sem_idx = sem_map.get(rec.semester, current_semester_index)
                    if current_semester_index - sem_idx > 1:
                        rec.grade = "F"

                # No transfer for capstones
                if rec.grade == "T" and code in CreditAuditor.CAPSTONES:
                    rec.status = "REJECTED-TRANSFER"
                    rec.grade = "F"
                    continue

                # B- retake threshold
                if passed_with_b_minus:
                    rec.status = "UNAUTHORIZED-RETAKE"
                    continue

                if rec.grade in PASSING_GRADES and grade_rank(rec.grade) >= grade_rank("B-"):
                    passed_with_b_minus = True

            # Pick BEST among valid attempts
            valid = [r for r in attempts if r.status not in ("UNAUTHORIZED-RETAKE", "REJECTED-TRANSFER")]
            if not valid:
                continue

            if len(valid) == 1:
                rec = valid[0]
                if rec.is_withdrawn:
                    rec.status = "WITHDRAWN"
                elif rec.is_transfer:
                    rec.status = "WAIVED"
                elif rec.is_passing:
                    rec.status = "BEST"
                elif rec.grade in ("F",) or rec.is_incomplete:
                    rec.status = "FAILED"
                else:
                    rec.status = "BEST"
            else:
                best = max(valid, key=lambda r: grade_rank(r.grade))
                for rec in valid:
                    if rec is best:
                        if rec.is_withdrawn:
                            rec.status = "WITHDRAWN"
                        elif rec.is_transfer:
                            rec.status = "WAIVED"
                        elif rec.is_passing:
                            rec.status = "BEST"
                        elif rec.grade in ("F",) or rec.is_incomplete:
                            rec.status = "FAILED"
                        else:
                            rec.status = "BEST"
                    else:
                        if rec.is_withdrawn:
                            rec.status = "WITHDRAWN"
                        else:
                            rec.status = "RETAKE-IGNORED"

        return records

    # ───────────────────────────────────────────────
    # Credit Calculation
    # ───────────────────────────────────────────────

    @staticmethod
    def calculate_credits(records: list[CourseRecord]) -> tuple[int, int]:
        """
        Returns (credits_attempted, credits_earned).

        Attempted: all credit-bearing attempts, excluding W, T, and 0-credit.
        Earned: passed courses (BEST/WAIVED status), one per course.
        """
        attempted = 0
        earned = 0
        for r in records:
            if r.credits > 0 and r.grade != "W" and r.grade != "T":
                attempted += r.credits
            if r.status in ("BEST", "WAIVED") and r.credits > 0 and r.is_passing:
                earned += r.credits
        return attempted, earned

    # ───────────────────────────────────────────────
    # Fake Transcript Detection
    # ───────────────────────────────────────────────

    @staticmethod
    def detect_fake_transcript(records: list[CourseRecord]) -> set[str]:
        """Return set of unrecognized course codes (not in NSU database)."""
        return {r.course_code for r in records
                if r.course_code not in ALL_COURSES and r.grade not in ("W", "I")}

    # ───────────────────────────────────────────────
    # Academic Dismissal Detection
    # ───────────────────────────────────────────────

    @staticmethod
    def detect_dismissal(records: list[CourseRecord]) -> dict:
        """
        Check for academic dismissal (3 consecutive semesters CGPA < 2.0).
        Returns dict with 'dismissed', 'dismissal_semester', 'cutoff_records', 'earned'.
        """
        from packages.core.cgpa_engine import CGPAAuditor

        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}
        transcript_sems = sorted(
            list(set(r.semester for r in records if r.semester in sem_map)),
            key=lambda s: sem_map[s],
        )

        consecutive_p = 0
        dismissal_sem = None
        cutoff_records = []

        for current_sem in transcript_sems:
            if dismissal_sem:
                break

            cutoff_idx = sem_map[current_sem]
            subset = [copy.copy(r) for r in records
                      if r.semester in sem_map and sem_map[r.semester] <= cutoff_idx]
            resolved_subset = CreditAuditor.resolve_retakes(subset)
            snap_cgpa, _, _ = CGPAAuditor.compute_cgpa(resolved_subset)

            cutoff_records.extend([r for r in records if r.semester == current_sem])

            if snap_cgpa < 2.0:
                consecutive_p += 1
                if consecutive_p >= 3:
                    dismissal_sem = current_sem
            else:
                consecutive_p = 0

        if dismissal_sem:
            earned = sum(r.credits for r in cutoff_records
                         if r.status in ("BEST", "WAIVED") and r.grade not in ("F", "W", "I"))
            return {
                "dismissed": True,
                "dismissal_semester": dismissal_sem,
                "cutoff_records": cutoff_records,
                "earned": earned,
            }

        return {"dismissed": False, "dismissal_semester": None,
                "cutoff_records": records, "earned": None}

    # ───────────────────────────────────────────────
    # Full Level 1 Pipeline
    # ───────────────────────────────────────────────

    @staticmethod
    def process(filepath: str) -> dict:
        """
        Full Level 1 pipeline: parse → resolve retakes → sort → calculate credits.

        Returns dict with: records, credits_attempted, credits_earned,
                           unrecognized (set), dismissal (dict).
        """
        records = TranscriptParser.parse(filepath)
        records = CreditAuditor.resolve_retakes(records)

        # Sort: prefix → number → suffix → semester
        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}

        def sort_key(r):
            code = r.course_code
            sem_idx = sem_map.get(r.semester, -1)
            match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', code)
            if match:
                prefix, num, suffix = match.groups()
                return (prefix, int(num), suffix, sem_idx)
            return (code, 0, "", sem_idx)

        records.sort(key=sort_key)

        attempted, earned = CreditAuditor.calculate_credits(records)
        unrecognized = CreditAuditor.detect_fake_transcript(records)

        return {
            "records": records,
            "credits_attempted": attempted,
            "credits_earned": earned,
            "unrecognized": unrecognized,
        }

    @staticmethod
    def process_rows(rows: list[dict]) -> dict:
        """
        Same as process() but accepts pre-parsed dict rows (from API/DB).

        Returns dict with: records, credits_attempted, credits_earned,
                           unrecognized (set).
        """
        records = TranscriptParser.parse_rows(rows)
        records = CreditAuditor.resolve_retakes(records)

        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}

        def sort_key(r):
            code = r.course_code
            sem_idx = sem_map.get(r.semester, -1)
            match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', code)
            if match:
                prefix, num, suffix = match.groups()
                return (prefix, int(num), suffix, sem_idx)
            return (code, 0, "", sem_idx)

        records.sort(key=sort_key)

        attempted, earned = CreditAuditor.calculate_credits(records)
        unrecognized = CreditAuditor.detect_fake_transcript(records)

        return {
            "records": records,
            "credits_attempted": attempted,
            "credits_earned": earned,
            "unrecognized": unrecognized,
        }
