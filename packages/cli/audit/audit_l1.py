#!/usr/bin/env python3
"""
audit_l1.py — Level 1: Credit Tallying Engine
Parses transcript CSV and calculates total earned credits.
Handles retakes (keeps best grade), withdrawals, and failing grades.
"""
import csv
import sys
from .style import (
    GR, RD, YL, CY, BL, DM, RS,
    H, V, TL, TR, BL2, BR, ML, MR, MC, TM, BM,
    CHK, XMK, WRN, ARW, BULL,
    visible_len, pad_row
)

GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

def is_passing_grade(grade):
    return grade.upper() not in ['F', 'W', 'I', 'X']

def status_display(status):
    icons = {
        'Counted':           f'{GR}{CHK}{RS}',
        'Retake (Ignored)':  f'{YL}{ARW}{RS}',
        'Illegal Retake':     f'{RD}{WRN}{RS}',
        'Failed':            f'{RD}{XMK}{RS}',
        'Withdrawn':         f'{YL}~{RS}',
        'Incomplete':        f'{YL}?{RS}',
        'Skipped':           f'{DM}-{RS}',
    }
    icon = icons.get(status, BULL)
    return f'{icon} {status}'


def calculate_credits(transcript_file):
    passed_courses = set()
    total_credits  = 0
    rows_display   = []

    try:
        with open(transcript_file, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            reader.fieldnames = [n.strip() for n in reader.fieldnames]
            entries = list(reader)

        passed_best = {}

        for row in entries:
            course = row.get('Course_Code', row.get('course_code', '')).strip()
            grade  = row.get('Grade', row.get('grade', '')).strip()
            try:    credits = float(row.get('Credits', row.get('credits', 0)))
            except: credits = 0.0

            pts = GRADE_POINTS.get(grade.upper())

            if is_passing_grade(grade):
                if course not in passed_best:
                    total_credits += credits
                    passed_best[course] = pts if pts is not None else 0.0
                    status = 'Counted'
                else:
                    if passed_best[course] >= 3.3:
                        status = 'Illegal Retake'
                    else:
                        status = 'Retake (Ignored)'
                    if pts is not None and pts > passed_best[course]:
                        passed_best[course] = pts
            else:
                g = grade.upper()
                status = {'W': 'Withdrawn', 'I': 'Incomplete'}.get(g, 'Failed')

            rows_display.append((course, credits, grade, status))

    except FileNotFoundError:
        print(f'{RD}Error:{RS} File "{transcript_file}" not found.')
        sys.exit(1)
    except Exception as e:
        print(f'{RD}Error:{RS} {e}')
        sys.exit(1)

    W  = 62
    C1, C2, C3, C4 = 14, 9, 7, 28

    def hl(l, m, r, f=H): print(l + (f+m+f).join([f*C1, f*C2, f*C3, f*C4]) + r)

    print()
    print(f'{TL}{H * W}{TR}')
    content = f'  {BL}{CY}CREDIT TALLY REPORT{RS}'
    print(pad_row(content, W, V, V))
    content = f'  {DM}Transcript : {transcript_file}{RS}'
    print(pad_row(content, W, V, V))
    print(f'{BL2}{H * W}{BR}')
    print()

    hl(TL, TM, TR)
    print(f'{V} {BL}{"Course":<{C1-1}}{RS}{V} {BL}{"Credits":>{C2-1}}{RS}{V} '
          f'{BL}{"Grade":<{C3-1}}{RS}{V} {BL}{"Status":<{C4-1}}{RS}{V}')
    hl(ML, MC, MR)

    for course, credits, grade, status in rows_display:
        disp    = status_display(status)
        row_content = f' {course:<{C1-1}}{V} {credits:>{C2-1}.1f}{V} {grade:<{C3-1}}{V} {disp}'
        vl = visible_len(row_content)
        total_inner = C1 + C2 + C3 + C4 + 3
        pad = total_inner - vl
        print(f'{V}{row_content}{" " * max(0,pad)}{V}')

    hl(ML, BM, MR)
    credit_str = f'{BL}{GR}{total_credits:.1f}{RS}'
    content = f'  {CHK}  Total Valid Earned Credits : {credit_str}'
    print(pad_row(content, W, V, V))
    print(f'{BL2}{H * W}{BR}')
    print()

    return {'total_credits': total_credits, 'rows': rows_display}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Level 1: Credit Tally Engine')
    parser.add_argument('transcript', help='Path to transcript CSV file')
    parser.add_argument('program_name', nargs='?', help='Program name (unused at L1)')
    parser.add_argument('program_knowledge', nargs='?', help='Program knowledge file (unused at L1)')
    args = parser.parse_args()
    calculate_credits(args.transcript)

if __name__ == '__main__':
    main()
