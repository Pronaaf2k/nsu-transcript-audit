import sys
sys.path.insert(0, 'F:/Github/nsu-transcript-audit/packages/cli')
sys.path.insert(0, 'F:/Github/nsu-transcript-audit')

import csv
import os
import tempfile
import pytest

from packages.cli.audit.audit_l1 import calculate_credits
from packages.cli.audit.audit_l2 import calculate_cgpa
from packages.cli.audit.audit_l3 import parse_program_knowledge, audit_student


def write_csv(filepath, rows):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Course_Code', 'Course_Name', 'Credits', 'Grade', 'Semester'])
        writer.writeheader()
        writer.writerows(rows)


class TestLevel1:
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
            finally:
                os.unlink(f.name)


class TestLevel2:
    def test_simple_cgpa_calculation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            write_csv(f.name, [
                {'Course_Code': 'CSE115', 'Course_Name': 'Prog I', 'Credits': '3', 'Grade': 'A', 'Semester': 'Spring2019'},
                {'Course_Code': 'MAT120', 'Course_Name': 'Calc I', 'Credits': '3', 'Grade': 'B', 'Semester': 'Spring2019'},
            ])
            try:
                result = calculate_cgpa(f.name)
                assert result['cgpa'] == 3.50
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
                assert result['consecutive_probation'] >= 1
            finally:
                os.unlink(f.name)


class TestLevel3:
    def test_parse_program_knowledge(self):
        prog_file = 'F:/Github/nsu-transcript-audit/packages/cli/program.md'
        if not os.path.exists(prog_file):
            pytest.skip("program.md not found")
        
        reqs = parse_program_knowledge(prog_file, 'Computer Science & Engineering')
        assert reqs['total_credits_required'] == 130
        assert reqs['min_cgpa'] == 2.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
