"""
GradeTrace Core — Transcript Parser

Parses CSV transcript files into CourseRecord objects.
"""

import csv
from packages.core.models import CourseRecord
from packages.core.course_catalog import ALL_COURSES


class TranscriptParser:
    """Parses CSV transcript files into lists of CourseRecord objects."""

    @staticmethod
    def parse(filepath: str) -> list[CourseRecord]:
        """Parse a transcript CSV file into a list of CourseRecord objects."""
        records = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 5:
                    continue
                if row[0].strip().lower() == "course_code":
                    continue
                records.append(CourseRecord(
                    course_code=row[0],
                    course_name=row[1],
                    credits=row[2],
                    grade=row[3],
                    semester=row[4],
                    all_courses=ALL_COURSES,
                ))
        return records

    @staticmethod
    def parse_rows(rows: list[dict]) -> list[CourseRecord]:
        """Parse a list of dicts (from JSON/DB) into CourseRecord objects.

        Each dict must have keys: course_code, course_name, credits, grade, semester.
        """
        records = []
        for row in rows:
            records.append(CourseRecord(
                course_code=row["course_code"],
                course_name=row["course_name"],
                credits=row["credits"],
                grade=row["grade"],
                semester=row["semester"],
                all_courses=ALL_COURSES,
            ))
        return records
