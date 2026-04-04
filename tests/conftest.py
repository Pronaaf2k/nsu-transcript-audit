"""
Test fixtures and helpers for the audit engine tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core"))

from packages.core.models import CourseRecord
from packages.core.course_catalog import ALL_COURSES


def make_record(course_code: str, credits: int, grade: str, semester: str) -> CourseRecord:
    """Create a CourseRecord for testing."""
    return CourseRecord(
        course_code=course_code,
        course_name=f"Course {course_code}",
        credits=credits,
        grade=grade,
        semester=semester,
        all_courses=ALL_COURSES,
    )


def cse_eligible_records() -> list[CourseRecord]:
    """A sample CSE student who is graduation-eligible."""
    return [
        make_record("CSE115", 3, "A", "Spring2019"),
        make_record("CSE115L", 1, "A", "Spring2019"),
        make_record("MAT120", 3, "A-", "Spring2019"),
        make_record("ENG102", 3, "A", "Spring2019"),
        make_record("CSE215", 3, "A", "Summer2019"),
        make_record("CSE215L", 1, "B+", "Summer2019"),
        make_record("MAT130", 3, "B", "Summer2019"),
        make_record("CSE225", 3, "A-", "Fall2019"),
        make_record("CSE225L", 1, "B", "Fall2019"),
        make_record("MAT250", 3, "B+", "Fall2019"),
        make_record("CSE173", 3, "A", "Spring2020"),
        make_record("CSE231", 3, "B+", "Spring2020"),
        make_record("CSE231L", 1, "A", "Spring2020"),
        make_record("MAT350", 3, "B", "Spring2020"),
        make_record("CSE299", 1, "A", "Summer2020"),
        make_record("CSE311", 3, "A-", "Fall2020"),
        make_record("CSE311L", 1, "B+", "Fall2020"),
        make_record("CSE323", 3, "B", "Fall2020"),
        make_record("CSE325", 3, "B+", "Fall2020"),
        make_record("CSE327", 3, "A", "Spring2021"),
        make_record("EEE141", 3, "B", "Spring2021"),
        make_record("EEE141L", 1, "A-", "Spring2021"),
        make_record("CSE331", 3, "B+", "Summer2021"),
        make_record("CSE331L", 1, "A", "Summer2021"),
        make_record("CSE332", 3, "B", "Fall2021"),
        make_record("CSE373", 3, "A-", "Fall2021"),
        make_record("PHY107", 3, "B+", "Fall2021"),
        make_record("PHY107L", 1, "A", "Fall2021"),
        make_record("CSE425", 3, "A", "Spring2022"),
        make_record("CSE421", 3, "B+", "Spring2022"),
        make_record("CSE422", 3, "A-", "Spring2022"),
        make_record("CSE499A", 2, "A", "Summer2022"),
        make_record("CSE499B", 2, "A", "Fall2022"),
        make_record("EEE452", 3, "B", "Fall2022"),
        make_record("ENG103", 3, "A", "Spring2019"),
        make_record("ENG105", 3, "A-", "Fall2019"),
        make_record("ENG111", 3, "B+", "Fall2019"),
        make_record("PHI101", 3, "A", "Spring2020"),
        make_record("PHI104", 3, "B", "Summer2020"),
        make_record("HIS101", 3, "A", "Fall2020"),
        make_record("HIS102", 3, "B+", "Fall2020"),
        make_record("ECO101", 3, "A-", "Spring2021"),
        make_record("POL101", 3, "B", "Summer2021"),
        make_record("SOC101", 3, "A", "Fall2021"),
        make_record("MAT116", 3, "A", "Spring2019"),
        make_record("MAT125", 3, "B+", "Fall2020"),
        make_record("MAT361", 3, "A-", "Spring2021"),
        make_record("PHY108", 3, "B", "Fall2021"),
        make_record("PHY108L", 1, "A", "Fall2021"),
        make_record("CHE101", 3, "B+", "Spring2022"),
        make_record("CHE101L", 1, "A-", "Spring2022"),
        make_record("BIO103", 3, "B", "Summer2022"),
        make_record("BIO103L", 1, "A", "Summer2022"),
        make_record("CEE110", 1, "A", "Fall2019"),
        make_record("EEE111", 3, "B+", "Spring2022"),
        make_record("EEE111L", 1, "A-", "Spring2022"),
    ]


def cse_probation_records() -> list[CourseRecord]:
    """A CSE student on academic probation."""
    return [
        make_record("CSE115", 3, "D", "Spring2019"),
        make_record("CSE115L", 1, "D+", "Spring2019"),
        make_record("MAT120", 3, "D+", "Spring2019"),
        make_record("ENG102", 3, "C", "Spring2019"),
        make_record("CSE215", 3, "F", "Summer2019"),
        make_record("CSE215L", 1, "F", "Summer2019"),
        make_record("MAT130", 3, "D", "Summer2019"),
        make_record("CSE225", 3, "D+", "Fall2019"),
        make_record("CSE225L", 1, "D", "Fall2019"),
        make_record("MAT250", 3, "D", "Fall2019"),
        make_record("CSE173", 3, "C-", "Spring2020"),
        make_record("CSE231", 3, "D+", "Spring2020"),
        make_record("CSE231L", 1, "D", "Spring2020"),
        make_record("MAT350", 3, "C-", "Summer2020"),
    ]


def bba_eligible_records() -> list[CourseRecord]:
    """A BBA student who is graduation-eligible."""
    return [
        make_record("ECO101", 3, "A", "Spring2019"),
        make_record("ECO104", 3, "A-", "Summer2019"),
        make_record("MIS107", 3, "B+", "Fall2019"),
        make_record("BUS172", 3, "A", "Fall2019"),
        make_record("BUS173", 3, "B+", "Spring2020"),
        make_record("BUS135", 3, "A-", "Spring2020"),
        make_record("ACT201", 3, "A", "Summer2020"),
        make_record("ACT202", 3, "B+", "Fall2020"),
        make_record("FIN254", 3, "A-", "Fall2020"),
        make_record("LAW200", 3, "B", "Spring2021"),
        make_record("INB372", 3, "A", "Spring2021"),
        make_record("MKT202", 3, "B+", "Summer2021"),
        make_record("MIS207", 3, "A-", "Summer2021"),
        make_record("MGT212", 3, "A", "Fall2021"),
        make_record("MGT351", 3, "B+", "Fall2021"),
        make_record("MGT314", 3, "A-", "Spring2022"),
        make_record("MGT368", 3, "B", "Spring2022"),
        make_record("MGT489", 3, "A", "Summer2022"),
        make_record("ENG103", 3, "A-", "Fall2019"),
        make_record("ENG105", 3, "B+", "Fall2019"),
        make_record("PHI401", 3, "A", "Spring2020"),
        make_record("ENG115", 3, "A-", "Summer2020"),
        make_record("HIS101", 3, "B+", "Fall2020"),
        make_record("HIS102", 3, "A", "Fall2020"),
        make_record("POL101", 3, "B", "Spring2021"),
        make_record("SOC101", 3, "A-", "Summer2021"),
        make_record("BIO103", 3, "B+", "Fall2021"),
        make_record("BIO103L", 1, "A", "Fall2021"),
        make_record("ENV107", 3, "A-", "Spring2022"),
        make_record("ENV107L", 1, "B+", "Spring2022"),
        make_record("PBH101", 3, "A", "Summer2022"),
        make_record("PBH101L", 1, "B+", "Summer2022"),
        make_record("BUS498", 4, "A", "Fall2022"),
        make_record("ENG102", 3, "A", "Spring2019"),
        make_record("BUS112", 3, "A-", "Spring2019"),
        make_record("ACT310", 3, "A", "Fall2022"),
        make_record("ACT320", 3, "B+", "Fall2022"),
        make_record("ACT360", 3, "A-", "Spring2023"),
        make_record("ACT370", 3, "B+", "Spring2023"),
        make_record("ACT380", 3, "A", "Summer2023"),
        make_record("FIN433", 3, "A-", "Fall2023"),
        make_record("FIN440", 3, "B+", "Fall2023"),
        make_record("FIN435", 3, "A", "Spring2024"),
        make_record("FIN444", 3, "B+", "Spring2024"),
    ]


def retake_records() -> list[CourseRecord]:
    """A student with retake scenarios."""
    return [
        make_record("CSE115", 3, "D", "Spring2019"),
        make_record("CSE115", 3, "B", "Summer2019"),
        make_record("MAT120", 3, "F", "Spring2019"),
        make_record("MAT120", 3, "C", "Summer2019"),
        make_record("CSE215", 3, "F", "Fall2019"),
        make_record("CSE215", 3, "B+", "Spring2020"),
        make_record("CSE225", 3, "B-", "Spring2020"),
        make_record("ENG102", 3, "A", "Spring2019"),
    ]


def incomplete_and_withdrawal_records() -> list[CourseRecord]:
    """A student with incomplete and withdrawal grades."""
    return [
        make_record("CSE115", 3, "A", "Spring2019"),
        make_record("MAT120", 3, "B", "Spring2019"),
        make_record("ENG102", 3, "I", "Summer2019"),
        make_record("CSE215", 3, "W", "Fall2019"),
        make_record("CSE225", 3, "A-", "Fall2019"),
        make_record("MAT130", 3, "B+", "Spring2020"),
    ]


def transfer_records() -> list[CourseRecord]:
    """A student with transfer credits (T grade)."""
    return [
        make_record("ENG102", 3, "T", "Spring2019"),
        make_record("CSE115", 3, "A", "Spring2019"),
        make_record("MAT120", 3, "B+", "Spring2019"),
        make_record("CSE215", 3, "A-", "Fall2019"),
        make_record("CSE225", 3, "B+", "Fall2019"),
    ]


def fake_transcript_records() -> list[CourseRecord]:
    """A transcript with invalid course codes."""
    return [
        make_record("CSE115", 3, "A", "Spring2019"),
        make_record("CSE215", 3, "B+", "Summer2019"),
        make_record("FAKE101", 3, "A", "Fall2019"),
        make_record("INVALID999", 3, "B", "Fall2019"),
        make_record("MAT120", 3, "A-", "Spring2019"),
    ]


def dismissal_records() -> list[CourseRecord]:
    """A student who should be dismissed (3 consecutive semesters < 2.0)."""
    return [
        make_record("CSE115", 3, "F", "Spring2019"),
        make_record("MAT120", 3, "F", "Spring2019"),
        make_record("ENG102", 3, "D", "Spring2019"),
        make_record("CSE215", 3, "F", "Summer2019"),
        make_record("MAT130", 3, "D", "Summer2019"),
        make_record("CSE225", 3, "F", "Summer2019"),
        make_record("CSE173", 3, "D+", "Fall2019"),
        make_record("CSE231", 3, "D", "Fall2019"),
    ]
