"""
Unit tests for the NSU Audit Engine.
Tests cover L1 (Credit Tallying), L2 (CGPA & Standing), and L3 (Graduation Audit).
"""

import csv
import os
import sys
import tempfile
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.cli.audit.audit_l1 import calculate_credits
from packages.cli.audit.audit_l2 import calculate_cgpa
from packages.cli.audit.audit_l3 import parse_program_knowledge, audit_student


def write_csv(filepath: str, rows: list[dict]):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Course_Code', 'Course_Name', 'Credits', 'Grade', 'Semester'])
        writer.writeheader()
        writer.writerows(rows)


class TestLevel1:
    """Level 1: Credit Tallying Tests"""

    def test_basic_credit_count(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Programming I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calculus I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Spring2019'},
                {'Course_Code': 'ENG102', 'Course_Name': 'Composition', 'Credits': '3', 'Grade': 'A-', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 9.0
            finally:
                os.unlink(f.name)

    def test_retake_picks_best_grade(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'D', 'Semester': 'Spring2019'},
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'B', 'Semester': 'Summer2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 3.0
                rows = result['rows']
                assert any(r[3] == 'Counted' and r[2] == 'B' for r in rows)
                assert any(r[3] == 'Retake (Ignored)' and r[2] == 'D' for r in rows)
            finally:
                os.unlink(f.name)

    def test_failed_course_not_counted(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'F', 'Semester': 'Spring2019'},
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'C', 'Semester': 'Summer2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 3.0
                rows = result['rows']
                assert any(r[3] == 'Failed' and r[2] == 'F' for r in rows)
                assert any(r[3] == 'Counted' and r[2] == 'C' for r in rows)
            finally:
                os.unlink(f.name)

    def test_withdrawn_not_counted(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'W', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 0.0
                assert result['rows'][0][3] == 'Withdrawn'
            finally:
                os.unlink(f.name)

    def test_incomplete_treated_as_failed(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'I', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 0.0
                assert result['rows'][0][3] == 'Incomplete'
            finally:
                os.unlink(f.name)

    def test_illegal_retake_b_plus_or_higher(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Spring2019'},
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Summer2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 3.0
                rows = result['rows']
                assert any(r[3] == 'Counted' and r[2] == 'B+' for r in rows)
                assert any(r[3] == 'Illegal Retake' and r[2] == 'A' for r in rows)
            finally:
                os.unlink(f.name)

    def test_transfer_waiver_counted(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'ENG102', 'Course_Name': 'Composition', 'Credits': '3', 'Grade': 'T', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_credits(f.name)
                assert result['total_credits'] == 3.0
            finally:
                os.unlink(f.name)


class TestLevel2:
    """Level 2: CGPA & Standing Tests"""

    def test_simple_cgpa_calculation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'B', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['cgpa'] == 3.50
                assert result['gpa_credits'] == 6.0
            finally:
                os.unlink(f.name)

    def test_cgpa_truncation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'B-', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                raw = (3.3 * 3 + 2.7 * 3) / 6
                expected = int(raw * 100) / 100
                assert result['cgpa'] == expected
            finally:
                os.unlink(f.name)

    def test_probation_detection(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'D', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'D+', 'Semester': 'Summer2019'},
                {'Course_Code': 'ENG102', 'Course_Name': 'Comp', 'Credits': '3', 'Grade': 'D', 'Semester': 'Fall2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['standing'] == 'PROBATION'
                assert result['consecutive_probation'] >= 1
            finally:
                os.unlink(f.name)

    def test_normal_standing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Summer2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['standing'] == 'NORMAL'
            finally:
                os.unlink(f.name)

    def test_semester_order(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Fall2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert len(result['semesters']) == 2
                sem_names = [s['semester'] for s in result['semesters']]
                assert 'Spring2019' in sem_names
                assert 'Fall2019' in sem_names
            finally:
                os.unlink(f.name)

    def test_waivers_excluded_from_gpa(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'ENG102', 'Course_Name': 'Comp', 'Credits': '3', 'Grade': 'T', 'Semester': 'Spring2019'},
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'B', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name, waivers=['ENG102'])
                assert result['gpa_credits'] == 3.0
                assert result['cgpa'] == 3.0
            finally:
                os.unlink(f.name)


class TestLevel3:
    """Level 3: Graduation Audit Tests"""

    def test_parse_program_knowledge(self):
        prog_file = os.path.join(os.path.dirname(__file__), '..', 'cli', 'program.md')
        if not os.path.exists(prog_file):
            pytest.skip("program.md not found")
        
        reqs = parse_program_knowledge(prog_file, 'Computer Science & Engineering')
        assert reqs['total_credits_required'] == 130
        assert reqs['min_cgpa'] == 2.0
        assert 'CSE115' in reqs['major_core']
        assert 'ENG102' in reqs['mandatory_ged']
        assert 'MAT120' in reqs['core_math']

    def test_eligible_student(self):
        prog_file = os.path.join(os.path.dirname(__file__), '..', 'cli', 'program.md')
        if not os.path.exists(prog_file):
            pytest.skip("program.md not found")
        
        reqs = parse_program_knowledge(prog_file, 'Computer Science & Engineering')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'CSE115L', 'Course_Name': 'Prog I Lab', 'Credits': '1', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'ENG102', 'Course_Name': 'Comp', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'ENG103', 'Course_Name': 'Int Comp', 'Credits': '3', 'Grade': 'A', 'Semester': 'Summer2019'},
                {'Course_Code': 'HIS103', 'Course_Name': 'Bangladesh', 'Credits': '3', 'Grade': 'A', 'Semester': 'Summer2019'},
                {'Course_Code': 'PHI101', 'Course_Name': 'Phil', 'Credits': '3', 'Grade': 'A', 'Semester': 'Fall2019'},
                {'Course_Code': 'BEN205', 'Course_Name': 'Bengali', 'Credits': '3', 'Grade': 'A', 'Semester': 'Fall2019'},
                {'Course_Code': 'POL101', 'Course_Name': 'Pol Sci', 'Credits': '3', 'Grade': 'A', 'Semester': 'Fall2019'},
                {'Course_Code': 'ECO101', 'Course_Name': 'Econ', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2020'},
                {'Course_Code': 'SOC101', 'Course_Name': 'Soc', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2020'},
                {'Course_Code': 'ENV203', 'Course_Name': 'Env', 'Credits': '3', 'Grade': 'A', 'Semester': 'Summer2020'},
            ])
            try:
                result = audit_student(f.name, reqs, md_file=prog_file)
                assert result['cgpa'] == 4.0
                assert result['total_earned'] >= reqs['total_credits_required']
            finally:
                os.unlink(f.name)

    def test_missing_courses_detected(self):
        prog_file = os.path.join(os.path.dirname(__file__), '..', 'cli', 'program.md')
        if not os.path.exists(prog_file):
            pytest.skip("program.md not found")
        
        reqs = parse_program_knowledge(prog_file, 'Computer Science & Engineering')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
            ])
            try:
                result = audit_student(f.name, reqs, md_file=prog_file)
                assert 'CSE115' not in result['missing']['Core']
                assert len(result['missing']['GED']) > 0
            finally:
                os.unlink(f.name)

    def test_low_cgpa_not_eligible(self):
        prog_file = os.path.join(os.path.dirname(__file__), '..', 'cli', 'program.md')
        if not os.path.exists(prog_file):
            pytest.skip("program.md not found")
        
        reqs = parse_program_knowledge(prog_file, 'Computer Science & Engineering')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'F', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'F', 'Semester': 'Spring2019'},
            ])
            try:
                result = audit_student(f.name, reqs, md_file=prog_file)
                assert result['cgpa'] == 0.0
                assert result['total_earned'] < reqs['total_credits_required']
            finally:
                os.unlink(f.name)


class TestGPAEdgeCases:
    """Edge cases for GPA calculations"""

    def test_empty_transcript(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [])
            try:
                result = calculate_cgpa(f.name)
                assert result['cgpa'] == 0.0
                assert result['gpa_credits'] == 0.0
                assert result['standing'] == 'NORMAL'
            finally:
                os.unlink(f.name)

    def test_all_withdrawals(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'W', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['cgpa'] == 0.0
                assert result['gpa_credits'] == 0.0
            finally:
                os.unlink(f.name)

    def test_case_insensitive_grades(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'a', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'B+', 'Semester': 'Summer2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['cgpa'] == 3.65
            finally:
                os.unlink(f.name)

    def test_all_grades_accounted(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'C1', 'Course_Name': 'C1', 'Credits': '3', 'Grade': 'A', 'Semester': 'S1'},
                {'Course_Code': 'C2', 'Course_Name': 'C2', 'Credits': '3', 'Grade': 'A-', 'Semester': 'S1'},
                {'Course_Code': 'C3', 'Course_Name': 'C3', 'Credits': '3', 'Grade': 'B+', 'Semester': 'S1'},
                {'Course_Code': 'C4', 'Course_Name': 'C4', 'Credits': '3', 'Grade': 'B', 'Semester': 'S1'},
                {'Course_Code': 'C5', 'Course_Name': 'C5', 'Credits': '3', 'Grade': 'B-', 'Semester': 'S1'},
                {'Course_Code': 'C6', 'Course_Name': 'C6', 'Credits': '3', 'Grade': 'C+', 'Semester': 'S1'},
                {'Course_Code': 'C7', 'Course_Name': 'C7', 'Credits': '3', 'Grade': 'C', 'Semester': 'S1'},
                {'Course_Code': 'C8', 'Course_Name': 'C8', 'Credits': '3', 'Grade': 'C-', 'Semester': 'S1'},
                {'Course_Code': 'C9', 'Course_Name': 'C9', 'Credits': '3', 'Grade': 'D+', 'Semester': 'S1'},
                {'Course_Code': 'C10', 'Course_Name': 'C10', 'Credits': '3', 'Grade': 'D', 'Semester': 'S1'},
            ])
            try:
                result = calculate_cgpa(f.name)
                expected = (4.0 + 3.7 + 3.3 + 3.0 + 2.7 + 2.3 + 2.0 + 1.7 + 1.3 + 1.0) / 10
                assert abs(result['cgpa'] - expected) < 0.01
            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
