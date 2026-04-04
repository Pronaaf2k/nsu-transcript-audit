#!/usr/bin/env python3
"""
audit_l3.py — Level 3: Graduation Audit with Deficiency Report
Compares transcript against program requirements to determine graduation eligibility.
Checks missing courses, prerequisite violations, and major declaration rules.
"""
import csv
import sys
import re
import argparse
from collections import defaultdict
from .style import (
    GR, RD, YL, CY, BL, DM, RS,
    H, V, TL, TR, BL2, BR, ML, MR,
    DH, DV, DTL, DTR, DBL, DBR, DML, DMR,
    CHK, XMK, WRN, BULL, SLP,
    visible_len, pad_row
)

GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
}

def is_passing(grade):
    return grade.upper() not in ['F', 'W', 'I', 'X']

SEMESTER_SEASON_ORDER = {'Spring': 0, 'Summer': 1, 'Fall': 2}

def semester_sort_key(sem_str):
    parts = sem_str.strip().split()
    if len(parts) == 2:
        try: return (int(parts[1]), SEMESTER_SEASON_ORDER.get(parts[0], 99))
        except: pass
    return (9999, 99)


def parse_global_courses(md_file):
    global_registry = {}
    in_req_section = False
    try:
        with open(md_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if re.match(r'^## \[Program:', line):
                    in_req_section = True
                    continue
                if not in_req_section:
                    continue
                if line.startswith('- **Prerequisites**:'):
                    in_req_section = False
                    continue
                cm = re.search(r'^\s*-\s*([A-Z]{2,4}\d{3}[A-Z]?):\s.*\((\d+) credit', line)
                if cm:
                    code = cm.group(1)
                    creds = int(cm.group(2))
                    if code not in global_registry:
                        global_registry[code] = creds
    except FileNotFoundError:
        pass
    return global_registry


def parse_program_knowledge(md_file, program_name):
    requirements = {
        'total_credits_required': 0,
        'min_cgpa': 2.0,
        'mandatory_ged': [],
        'core_math': [],
        'major_core': [],
        'core_business': [],
        'core_science': [],
        'prerequisites': {},
        'major_declaration_credits': 0,
        'elective_cap': 0,
    }

    current_section = None
    target_program_found = False
    fixed_credits = 0

    try:
        with open(md_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            program_match = re.match(r'^## \[Program: (.*)\]', line)
            if program_match:
                if program_match.group(1).strip() == program_name:
                    target_program_found = True
                    current_section = 'PROGRAM_HEADER'
                    fixed_credits = 0
                else:
                    target_program_found = False
                    current_section = None
                continue

            if not target_program_found:
                continue

            if line.startswith('- **Total Credits Required**:'):
                requirements['total_credits_required'] = int(re.search(r'\d+', line).group())
            elif line.startswith('- **Major Declaration Credits**:'):
                requirements['major_declaration_credits'] = int(re.search(r'\d+', line).group())
            elif line.startswith('- **Mandatory GED**:'):
                current_section = 'GED'
            elif line.startswith('- **Core Math**:'):
                current_section = 'MATH'
            elif line.startswith('- **Major Core**:'):
                current_section = 'CORE'
            elif line.startswith('- **Core Business**:'):
                current_section = 'BUSINESS'
            elif line.startswith('- **Core Science**:'):
                current_section = 'SCIENCE'
            elif line.startswith('- **Prerequisites**:'):
                current_section = 'PREREQS'

            if current_section == 'PREREQS':
                prereq_match = re.match(r'^\s*-\s*([A-Z]{2,4}\d{3}[A-Z]?):\s*([A-Z]{2,4}\d{3}[A-Z]?)$', line)
                if prereq_match:
                    requirements['prerequisites'][prereq_match.group(1)] = prereq_match.group(2)
                continue

            course_match = re.search(r'^\s*-\s*([A-Z]{2,4}\d{3}[A-Z]?):\s.*\((\d+) credit', line)
            if course_match and current_section not in (None, 'PROGRAM_HEADER', 'PREREQS'):
                course_code = course_match.group(1)
                creds       = int(course_match.group(2))
                fixed_credits += creds
                if current_section == 'GED':
                    requirements['mandatory_ged'].append(course_code)
                elif current_section == 'MATH':
                    requirements['core_math'].append(course_code)
                elif current_section == 'CORE':
                    requirements['major_core'].append(course_code)
                elif current_section == 'BUSINESS':
                    requirements['core_business'].append(course_code)
                elif current_section == 'SCIENCE':
                    requirements['core_science'].append(course_code)

    except FileNotFoundError:
        print(f"Error: Program file '{md_file}' not found.")
        sys.exit(1)

    requirements['elective_cap'] = max(0, requirements['total_credits_required'] - fixed_credits)
    return requirements


def audit_student(transcript_file, requirements, md_file='program.md'):
    rows = []
    try:
        with open(transcript_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            for row in reader:
                rows.append({
                    'course':  row.get('Course_Code', row.get('course_code', '')).strip(),
                    'grade':   row.get('Grade', row.get('grade', '')).strip(),
                    'credits': float(row.get('Credits', row.get('credits', 0))),
                    'semester': row.get('Semester', row.get('semester', 'Unknown')).strip(),
                })
    except FileNotFoundError:
        print(f"Error: Transcript '{transcript_file}' not found.")
        sys.exit(1)

    rows.sort(key=lambda r: semester_sort_key(r['semester']))

    sem_to_courses = defaultdict(set)
    for r in rows:
        sem_to_courses[r['semester']].add(r['course'])

    passed_courses = set()
    course_history = {}
    advisories = []
    prereqs = requirements.get('prerequisites', {})
    major_decl_credits = requirements.get('major_declaration_credits', 0)

    major_course_set = set(requirements['major_core'] + requirements['core_business'])

    passed_before_semester = set()
    credits_before_semester = 0.0
    prev_sem = None

    for r in rows:
        course  = r['course']
        grade   = r['grade']
        credits = r['credits']
        sem     = r['semester']

        if sem != prev_sem:
            passed_before_semester = set(passed_courses)
            credits_before_semester = 0.0
            for c in passed_courses:
                ch = course_history.get(c)
                if ch:
                    credits_before_semester += ch['credits']
            prev_sem = sem

        if course in prereqs:
            needed = prereqs[course]
            if needed not in passed_before_semester:
                advisories.append(
                    f'Prerequisite violation: {course} taken in {sem} '
                    f'without passing {needed} first'
                )

        if major_decl_credits > 0 and course in major_course_set:
            if credits_before_semester < major_decl_credits:
                advisories.append(
                    f'Major declaration: {course} taken in {sem} '
                    f'with only {credits_before_semester:.0f} earned credits '
                    f'(major courses require {major_decl_credits} credits first)'
                )

        if grade.upper() == 'T':
            passed_courses.add(course)
        elif is_passing(grade):
            passed_courses.add(course)

        if grade.upper() != 'T' and GRADE_POINTS.get(grade) is not None:
            points = GRADE_POINTS[grade]
            existing = course_history.get(course)
            if existing is not None and existing['points'] >= 3.3:
                advisories.append(
                    f'Illegal retake: {course} retaken in {sem} '
                    f'while already holding {existing["grade"]} '
                    f'(B+ or higher cannot be retaken)'
                )
            if existing is None or points > existing['points']:
                course_history[course] = {'grade': grade, 'credits': credits, 'points': points}

    all_known_courses = set(
        requirements['mandatory_ged'] + requirements['core_math'] +
        requirements['major_core'] + requirements['core_business'] +
        requirements['core_science']
    )
    seen_lab_violations = set()
    for r in rows:
        course  = r['course']
        credits = r['credits']
        sem     = r['semester']
        if credits == 0 and course.startswith('CSE') and course.endswith('L'):
            main = course[:-1]
            if main in all_known_courses and course in all_known_courses:
                if main not in sem_to_courses[sem]:
                    key = (course, sem)
                    if key not in seen_lab_violations:
                        seen_lab_violations.add(key)
                        advisories.append(
                            f'Co-registration: {course} (0-credit lab) taken in {sem} '
                            f'without {main} enrolled in the same semester'
                        )

    if 'CSE498R' in course_history:
        if 'BIO103L' in passed_courses:
            course_history['CSE498R']['credits'] = 0.0
        else:
            course_history['CSE498R']['credits'] = 1.0

    gpa_points = 0.0
    gpa_credits = 0.0
    for data in course_history.values():
        if data['credits'] > 0:
            gpa_points += data['points'] * data['credits']
            gpa_credits += data['credits']
    raw_cgpa = gpa_points / gpa_credits if gpa_credits > 0 else 0.0
    cgpa = int(raw_cgpa * 100) / 100.0
    
    missing = {
        'GED': [], 'Math': [], 'Core': [], 'Science': [], 'Business': []
    }

    equivalent_courses = {'MAT112': 'BUS112', 'BUS112': 'MAT112'}

    expanded_passed = set(passed_courses)
    for c in passed_courses:
        if c in equivalent_courses:
            expanded_passed.add(equivalent_courses[c])

    for req in requirements['mandatory_ged']:
        if req not in expanded_passed: missing['GED'].append(req)
    for req in requirements['core_math']:
        if req not in expanded_passed: missing['Math'].append(req)
    for req in requirements['major_core']:
        if req not in expanded_passed: missing['Core'].append(req)
    for req in requirements['core_science']:
        if req not in expanded_passed: missing['Science'].append(req)
    for req in requirements['core_business']:
        if req not in expanded_passed: missing['Business'].append(req)

    all_reqs = set(
        requirements['mandatory_ged'] + requirements['core_math'] +
        requirements['major_core']    + requirements['core_business'] +
        requirements['core_science']
    )

    global_registry = parse_global_courses(md_file)

    elective_cap        = requirements.get('elective_cap', 0)
    free_elective_used  = 0.0
    free_electives      = []
    excess_electives    = []
    invalid_electives   = []
    total_earned_credits = 0.0

    for course in passed_courses:
        is_req = course in all_reqs or (
            course in equivalent_courses and equivalent_courses[course] in all_reqs)
        curr = course_history.get(course)
        if curr and is_req:
            total_earned_credits += curr['credits']

    seen_order = []
    for r in rows:
        c = r['course']
        if c in passed_courses and c not in all_reqs and c not in seen_order:
            seen_order.append(c)

    for course in seen_order:
        is_req = course in all_reqs or (
            course in equivalent_courses and equivalent_courses[course] in all_reqs)
        if is_req:
            continue
        curr = course_history.get(course)
        if not curr:
            continue
        creds = curr['credits']
        if course in global_registry or course in equivalent_courses:
            total_earned_credits += creds
            free_elective_used   += creds
            free_electives.append((course, creds))
            if free_elective_used > elective_cap:
                excess_electives.append((course, creds))
        else:
            invalid_electives.append(course)


    return {
        'total_earned':     total_earned_credits,
        'cgpa':             cgpa,
        'missing':          missing,
        'invalid_electives': invalid_electives,
        'free_electives':   free_electives,
        'excess_electives': excess_electives,
        'elective_cap':     elective_cap,
        'elective_used':    free_elective_used,
        'passed_courses':   passed_courses,
        'advisories':       advisories,
    }


def print_report(audit, requirements, program_name):
    W   = 64
    req = requirements['total_credits_required']
    min_cgpa   = requirements['min_cgpa']
    earned     = audit['total_earned']
    cgpa       = audit['cgpa']
    cgpa_ok    = cgpa >= min_cgpa
    credits_ok = earned >= req
    has_missing = any(len(m) > 0 for m in audit['missing'].values())
    has_invalid = len(audit['invalid_electives']) > 0
    is_eligible = cgpa_ok and credits_ok and not has_missing and not has_invalid

    def cc(val, threshold): return GR if val >= threshold else RD

    print()
    print(f'╔{"═" * W}╗')
    label = 'GRADUATION AUDIT REPORT'
    content = f'  {BL}{CY}{label}{RS}'
    print(pad_row(content, W, '║', '║'))
    prog_line = f'Program  :  {program_name}'
    content = f'  {DM}{prog_line}{RS}'
    print(pad_row(content, W, '║', '║'))
    print(f'╠{"═" * W}╣')

    cred_c = cc(earned, req)
    cgpa_c = cc(cgpa, min_cgpa)
    cr_str = f'{cred_c}{BL}{earned:.1f}{RS}'
    cg_str = f'{cgpa_c}{BL}{cgpa:.2f}{RS}'
    content = f'  Credits Required : {BL}{req:<8}{RS}  │  Credits Earned : {cr_str}'
    print(pad_row(content, W, '║', '║'))
    content = f'  Min CGPA         : {BL}{min_cgpa:<8}{RS}  │  CGPA Earned    : {cg_str}'
    print(pad_row(content, W, '║', '║'))
    print(f'╠{"═" * W}╣')

    if is_eligible:
        verdict = '✓   ELIGIBLE FOR GRADUATION'
        vc = GR
    else:
        verdict = '✗   NOT ELIGIBLE FOR GRADUATION'
        vc = RD
    content = f'  {vc}{BL}{verdict}{RS}'
    print(pad_row(content, W, '║', '║'))
    print(f'╚{"═" * W}╝')

    if is_eligible and not audit.get('advisories'):
        print()
        return

    if not is_eligible:
        print(f'\n  {BL}DEFICIENCY REPORT{RS}')
        print(f'  {"─" * (W - 2)}')

        if not cgpa_ok:
            msg = f'CGPA {cgpa:.2f} is below the required minimum of {min_cgpa:.2f}'
            print(f'  {RD}⚠  Probation :{RS}  {msg}')

        if not credits_ok:
            gap = req - earned
            print(f'  {YL}⚠  Credits   :{RS}  Need {BL}{gap:.1f}{RS} more credits to reach {req}')

        if has_invalid:
            print(f'\n  {YL}⊘  Invalid Electives (credits excluded):{RS}')
            for course in audit['invalid_electives']:
                print(f'       •  {course}')


        categories_map = {
            'GED':      'General Education',
            'Math':     'Core Mathematics',
            'Core':     'Major Core',
            'Science':  'Core Science',
            'Business': 'Core Business',
        }
        missing_count = 0
        for cat_key, cat_name in categories_map.items():
            missing_list = audit['missing'].get(cat_key, [])
            if missing_list:
                n = len(missing_list)
                print(f'\n  {RD}✗  Missing {cat_name}{RS}  ({n} course{"s" if n>1 else ""})')
                for course in missing_list:
                    print(f'       •  {course}')
                missing_count += n

        if missing_count == 0 and not has_invalid:
            print(f'\n  {GR}✓  All subject requirements satisfied.{RS}')

        print(f'\n  {"─" * (W - 2)}')

    all_advisories = list(audit.get('advisories', []))
    excess = audit.get('excess_electives', [])
    if excess:
        cap  = audit.get('elective_cap', 0)
        used = audit.get('elective_used', 0)
        note = (f'Elective overload: {used:.0f} free elective credits taken but program '
                f'only needs {cap:.0f}. The following count toward graduation '
                f'but are beyond the program\'s elective quota — '
                f'consider declaring which {cap:.0f} cr to use:')
        all_advisories.insert(0, note)
        for (course, creds) in excess:
            all_advisories.insert(1, f'       •  {course} ({creds:.0f} cr — excess)')
    if all_advisories:
        print(f'\n  {BL}ADVISORY NOTES{RS}')
        print(f'  {"─" * (W - 2)}')
        for note in all_advisories:
            print(f'  {YL}⚠{RS}  {note}')
        print(f'  {"─" * (W - 2)}')

    free_elec = audit.get('free_electives', [])
    if free_elec and is_eligible:
        cap  = audit.get('elective_cap', 0)
        used = audit.get('elective_used', 0)
        print(f'\n  {BL}FREE ELECTIVES USED ({used:.0f}/{cap:.0f} cr){RS}')
        print(f'  {"─" * (W - 2)}')
        for (course, creds) in free_elec:
            print(f'       •  {course}  ({creds:.0f} cr)')
        print(f'  {"─" * (W - 2)}')

    print()

    return {
        'eligible': is_eligible,
        'total_earned': earned,
        'cgpa': cgpa,
        'missing': audit['missing'],
        'advisories': all_advisories
    }


def main():
    parser = argparse.ArgumentParser(description="Level 3: Audit & Deficiency Reporter")
    parser.add_argument('transcript', help="Path to transcript CSV file")
    parser.add_argument('program_name', nargs='?', default="Computer Science & Engineering", help="Full Header Name in Markdown")
    parser.add_argument('program_knowledge', nargs='?', default="program.md", help="Path to program knowledge file")
    
    args = parser.parse_args()
    
    program_map = {
        "CSE":   "Computer Science & Engineering",
        "ETE":   "Electronic & Telecom Engineering",
        "ENV":   "Environmental Science & Management",
        "ENG":   "English",
        "BBA":   "Business Administration",
        "ECO":   "Economics",
    }
    
    full_program_name = program_map.get(args.program_name.upper(), args.program_name)
    
    requirements = parse_program_knowledge(args.program_knowledge, full_program_name)

    result = audit_student(args.transcript, requirements, md_file=args.program_knowledge)
    
    print_report(result, requirements, full_program_name)

    return result

if __name__ == '__main__':
    main()
