#!/usr/bin/env python3
"""
audit_l2.py — Level 2: Semester-by-Semester CGPA Calculator
Displays per-semester and cumulative GPA with academic standing.
Handles retakes, waivers, transfer credits, and probation detection.
"""
import csv
import sys
import argparse
from collections import defaultdict
from .style import (
    GR, RD, YL, CY, BL, DM, RS,
    H, V, TL, TR, BL2, BR, ML, MR, MC, TM, BM,
    DH, DV, DTL, DTR, DBL, DBR, DML, DMR,
    CHK, XMK, WRN, ARW, BULL, SLP,
    visible_len, pad_row
)

GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'F': 0.0
}

SEMESTER_SEASON_ORDER = {'Spring': 0, 'Summer': 1, 'Fall': 2}

def semester_sort_key(sem_str):
    parts = sem_str.strip().split()
    if len(parts) == 2:
        try: return (int(parts[1]), SEMESTER_SEASON_ORDER.get(parts[0], 99))
        except: pass
    return (9999, 99)

def get_grade_points(grade):
    return GRADE_POINTS.get(grade.strip().upper(), None)

def grade_status_label(grade):
    g = grade.strip().upper()
    if g == 'W':  return 'Withdrawn'
    if g == 'I':  return 'Incomplete'
    if g == 'F':  return 'Failed'
    if get_grade_points(g) is not None: return 'Counted'
    return 'N/A'

def status_display(status):
    icons = {
        'Counted':           f'{GR}✓{RS}',
        'Withdrawn':         f'{YL}~{RS}',
        'Incomplete':        f'{YL}?{RS}',
        'Failed':            f'{RD}✗{RS}',
        'N/A':               f'{DM}–{RS}',
        'Waived':            f'{CY}⊘{RS}',
        'Retake (Ignored)':  f'{YL}↩{RS}',
        'Illegal Retake':    f'{RD}⚠{RS}',
    }
    return f'{icons.get(status,"·")} {status}'

def cgpa_colour(cgpa):
    if cgpa >= 3.0:  return GR
    if cgpa >= 2.0:  return YL
    return RD

def calculate_cgpa(transcript_file, waivers=None):
    if waivers is None: waivers = []
    waiver_set = {w.upper() for w in waivers}

    semester_rows = defaultdict(list)
    try:
        with open(transcript_file, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            for row in reader:
                sem = row.get('Semester', row.get('semester', 'Unknown')).strip()
                semester_rows[sem].append(row)
    except FileNotFoundError:
        print(f'{RD}Error:{RS} File "{transcript_file}" not found.')
        sys.exit(1)

    sorted_sems = sorted(semester_rows.keys(), key=semester_sort_key)

    W = 66
    print()
    print(f'╔{"═" * W}╗')
    title = 'SEMESTER-BY-SEMESTER CGPA REPORT'
    content = f'  {BL}{CY}{title}{RS}'
    print(pad_row(content, W, '║', '║'))
    content = f'  {DM}Transcript : {transcript_file}{RS}'
    print(pad_row(content, W, '║', '║'))
    if waivers:
        wl = f'Waivers    : {", ".join(waivers)}'
        content = f'  {DM}{wl}{RS}'
        print(pad_row(content, W, '║', '║'))
    print(f'╚{"═" * W}╝')

    cumulative_best    = {}
    consecutive_prob   = 0

    SW = W - 2

    for sem in sorted_sems:
        rows = semester_rows[sem]

        sem_label = f' {BL}{sem}{RS} '
        sem_vis = visible_len(sem_label)
        print(f'\n  ┌─{sem_label}{"─" * max(0, SW - sem_vis - 1)}┐')

        C1, C2, C3, C4 = 14, 9, 7, 20
        header_content = f'  {BL}{"Course":<{C1}}{RS} {BL}{"Credits":>{C2}}{RS}  {BL}{"Grade":<{C3}}{RS}  {BL}{"Status":<{C4}}{RS}'
        print(pad_row(header_content, SW, '  │', '│'))
        print(f'  ├{"─" * SW}┤')

        sem_pts  = 0.0
        sem_cred = 0.0

        for row in rows:
            course  = row.get('Course_Code', row.get('course_code', '')).strip()
            grade   = row.get('Grade', row.get('grade', '')).strip()
            try:    credits = float(row.get('Credits', row.get('credits', 0)))
            except: credits = 0.0

            is_waived = course.upper() in waiver_set or grade.upper() == 'T'
            if is_waived:
                label = status_display('Waived')
            else:
                points = get_grade_points(grade)
                ex = cumulative_best.get(course)

                if ex is not None:
                    if ex['points'] >= 3.3:
                        label = status_display('Illegal Retake')
                    else:
                        label = status_display('Retake (Ignored)')
                else:
                    label = status_display(grade_status_label(grade))

            row_content = f'  {course:<{C1}} {credits:>{C2}.1f}  {grade:<{C3}}  {label}'
            print(pad_row(row_content, SW, '  │', '│'))

            if not is_waived:
                if points is not None and credits > 0:
                    sem_pts  += points * credits
                    sem_cred += credits

                if points is not None:
                    if ex is None or points > ex['points']:
                        cumulative_best[course] = {'credits': credits, 'grade': grade, 'points': points}

        raw_tgpa = sem_pts / sem_cred if sem_cred > 0 else 0.0
        tgpa = int(raw_tgpa * 100) / 100.0
        cgpa_pts   = sum(d['points'] * d['credits'] for d in cumulative_best.values() if d['credits'] > 0)
        cgpa_creds = sum(d['credits']               for d in cumulative_best.values() if d['credits'] > 0)
        raw_cgpa = cgpa_pts / cgpa_creds if cgpa_creds > 0 else 0.0
        cgpa = int(raw_cgpa * 100) / 100.0

        if cgpa_creds > 0 and cgpa < 2.0:
            consecutive_prob += 1
        else:
            consecutive_prob = 0

        cc = cgpa_colour(cgpa)
        tc = cgpa_colour(tgpa)

        print(f'  ├{"─" * SW}┤')
        summary_content = (f'  Sem Credits : {BL}{sem_cred:<5.1f}{RS}  '
                          f'TGPA : {BL}{tc}{tgpa:.2f}{RS}   '
                          f'│   Cumulative CGPA : {BL}{cc}{cgpa:.2f}{RS}')
        print(pad_row(summary_content, SW, '  │', '│'))

        if consecutive_prob > 0:
            msg = f'⚠  ACADEMIC PROBATION  (semester {consecutive_prob} below 2.00)'
            standing_content = f'  {RD}{BL}{msg}{RS}'
        else:
            standing_content = f'  {GR}✓  Good Standing{RS}'
        print(pad_row(standing_content, SW, '  │', '│'))

        print(f'  └{"─" * SW}┘')

    f_pts   = sum(d['points'] * d['credits'] for d in cumulative_best.values() if d['credits'] > 0)
    f_creds = sum(d['credits']               for d in cumulative_best.values() if d['credits'] > 0)
    f_cgpa  = int((f_pts / f_creds) * 100) / 100.0 if f_creds > 0 else 0.0
    fc = cgpa_colour(f_cgpa)

    print()
    print(f'╔{"═" * W}╗')
    content = f'  {BL}FINAL SUMMARY{RS}'
    print(pad_row(content, W, '║', '║'))
    print(f'╠{"═" * W}╣')
    content = f'  Final CGPA               :  {BL}{fc}{f_cgpa:.2f}{RS}'
    print(pad_row(content, W, '║', '║'))
    content = f'  Total GPA-Bearing Credits :  {BL}{f_creds:.1f}{RS}'
    print(pad_row(content, W, '║', '║'))

    if consecutive_prob > 0:
        msg = f'⚠  Currently on ACADEMIC PROBATION  ({consecutive_prob} consecutive semester(s))'
        print(f'╠{"═" * W}╣')
        content = f'  {RD}{BL}{msg}{RS}'
        print(pad_row(content, W, '║', '║'))
    else:
        print(f'╠{"═" * W}╣')
        content = f'  {GR}✓  Student is in Good Standing{RS}'
        print(pad_row(content, W, '║', '║'))
    print(f'╚{"═" * W}╝')
    print()

    return {'cgpa': f_cgpa, 'gpa_credits': f_creds, 'consecutive_prob': consecutive_prob}


def main():
    parser = argparse.ArgumentParser(description='Level 2: Semester-by-Semester CGPA Calculator')
    parser.add_argument('transcript',        help='Path to transcript CSV file')
    parser.add_argument('program_name',      nargs='?', help='Program name (unused at L2)')
    parser.add_argument('program_knowledge', nargs='?', help='Program knowledge file (unused at L2)')
    parser.add_argument('--waivers',         help='Comma-separated course codes to waive', default='')
    args = parser.parse_args()

    waiver_list = []
    if args.waivers:
        waiver_list = [w.strip() for w in args.waivers.split(',') if w.strip()]
    else:
        print(f'\n{CY}Waivers{RS} — enter course codes to exclude (comma-separated), or press Enter for none:')
        user_input = input('  > ')
        if user_input.strip():
            waiver_list = [w.strip() for w in user_input.split(',')]

    calculate_cgpa(args.transcript, waivers=waiver_list)

if __name__ == '__main__':
    main()
