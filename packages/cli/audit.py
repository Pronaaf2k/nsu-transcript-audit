#!/usr/bin/env python3
"""
audit.py — Unified NSU Audit Engine
CLI tool that runs L1/L2/L3 audits on student transcripts.
Supports CSE, BBA, ETE, ENV, ENG, and ECO programs.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from audit.audit_l1 import calculate_credits
from audit.audit_l2 import calculate_cgpa
from audit.audit_l3 import parse_program_knowledge, audit_student, print_report
from audit.style import CY, GR, RD, BL, DM, RS, pad_row, hline_double, DTL, DH, DTR, DML, DMR

PROGRAM_MAP = {
    "CSE":   "Computer Science & Engineering",
    "ETE":   "Electronic & Telecom Engineering",
    "ENV":   "Environmental Science & Management",
    "ENG":   "English",
    "BBA":   "Business Administration",
    "ECO":   "Economics",
}

def print_banner(level, program, transcript):
    W = 64
    print()
    print(f'{DTL}{DH * W}{DTR}')
    level_names = {
        'l1': 'Level 1: Credit Tallying',
        'l2': 'Level 2: CGPA & Standing',
        'l3': 'Level 3: Graduation Audit',
        'full': 'Full Audit Report (L1 + L2 + L3)'
    }
    content = f'  {BL}{CY}NSU Transcript Audit — {level_names.get(level, level)}{RS}'
    print(pad_row(content, W, '║', '║'))
    content = f'  {DM}Program    : {program}{RS}'
    print(pad_row(content, W, '║', '║'))
    content = f'  {DM}Transcript : {transcript}{RS}'
    print(pad_row(content, W, '║', '║'))
    print(f'{DML}{DH * W}{DMR}')


def run_level1(transcript):
    calculate_credits(transcript)


def run_level2(transcript, waivers=None):
    calculate_cgpa(transcript, waivers=waivers)


def run_level3(transcript, program, program_file=None):
    if program_file is None:
        program_file = os.path.join(os.path.dirname(__file__), 'program.md')
    full_name = PROGRAM_MAP.get(program.upper(), program)
    print_banner('l3', full_name, transcript)
    print()
    requirements = parse_program_knowledge(program_file, full_name)
    result = audit_student(transcript, requirements, md_file=program_file)
    print_report(result, requirements, full_name)
    return result


def run_full(transcript, program, program_file=None, waivers=None):
    if program_file is None:
        program_file = os.path.join(os.path.dirname(__file__), 'program.md')
    full_name = PROGRAM_MAP.get(program.upper(), program)
    print_banner('full', full_name, transcript)
    
    print(f'\n  {BL}─── Level 1: Credit Tallying ───{RS}')
    print(f'  {DM}(Detailed in L1 report){RS}\n')
    from audit.audit_l1 import calculate_credits as calc_credits
    l1_result = calc_credits(transcript)
    
    print(f'\n  {BL}─── Level 2: CGPA & Standing ───{RS}')
    print(f'  {DM}(Detailed in L2 report){RS}\n')
    from audit.audit_l2 import calculate_cgpa as calc_cgpa
    l2_result = calc_cgpa(transcript, waivers=waivers)
    
    print(f'\n  {BL}─── Level 3: Graduation Audit ───{RS}\n')
    requirements = parse_program_knowledge(program_file, full_name)
    l3_result = audit_student(transcript, requirements, md_file=program_file)
    print_report(l3_result, requirements, full_name)
    
    print(f'\n  {BL}═══ EXECUTIVE SUMMARY ═══{RS}')
    W = 64
    print(f'╔{"═" * W}╗')
    req = requirements['total_credits_required']
    min_cgpa = requirements['min_cgpa']
    earned = l3_result['total_earned']
    cgpa = l3_result['cgpa']
    
    is_eligible = (
        cgpa >= min_cgpa and
        earned >= req and
        not any(len(m) > 0 for m in l3_result['missing'].values()) and
        not l3_result['invalid_electives']
    )
    
    if is_eligible:
        status = f'{GR}✓ ELIGIBLE FOR GRADUATION{RS}'
    else:
        status = f'{RD}✗ NOT ELIGIBLE FOR GRADUATION{RS}'
    
    content = f'  {BL}Status              : {status}{RS}'
    print(pad_row(content, W, '║', '║'))
    
    cred_color = GR if earned >= req else RD
    cgpa_color = GR if cgpa >= min_cgpa else RD
    content = f'  {BL}Credits             : {cred_color}{earned:.1f}{RS} / {req:.0f} required'
    print(pad_row(content, W, '║', '║'))
    content = f'  {BL}CGPA                : {cgpa_color}{cgpa:.2f}{RS} / {min_cgpa:.2f} minimum'
    print(pad_row(content, W, '║', '║'))
    
    total_missing = sum(len(m) for m in l3_result['missing'].values())
    content = f'  {BL}Missing Requirements : {RD}{total_missing}{RS} courses'
    print(pad_row(content, W, '║', '║'))
    
    print(f'╚{"═" * W}╝')
    print()

    return {
        'level1': l1_result,
        'level2': l2_result,
        'level3': l3_result,
        'eligible': is_eligible
    }


def main():
    parser = argparse.ArgumentParser(
        description='NSU Transcript Audit Engine — L1/L2/L3 Auditing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audit.py transcript.csv --level 1
  python audit.py transcript.csv --level 2 --waivers ENG102
  python audit.py transcript.csv --level 3 --program CSE --program-file program.md
  python audit.py transcript.csv --level full --program CSE
        """
    )
    
    parser.add_argument('transcript', help='Path to transcript CSV file')
    parser.add_argument('--level', '-l', default='full',
                        choices=['1', '2', '3', 'full'], help='Audit level (default: full)')
    parser.add_argument('--program', '-p', default='CSE',
                        help='Program code: CSE, BBA, ETE, ENV, ENG, ECO (default: CSE)')
    parser.add_argument('--program-file', default='program.md',
                        help='Path to program knowledge markdown file')
    parser.add_argument('--waivers', 
                        help='Comma-separated course codes to waive (e.g., ENG102,BUS112)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.transcript):
        print(f'{RD}Error:{RS} File not found: {args.transcript}')
        sys.exit(1)
    
    if not os.path.exists(args.program_file):
        print(f'{RD}Error:{RS} Program file not found: {args.program_file}')
        print(f'{DM}Using built-in program data instead...{RS}')
    
    waivers = None
    if args.waivers:
        waivers = [w.strip() for w in args.waivers.split(',') if w.strip()]
    
    level = args.level
    
    if level == '1':
        print_banner('l1', args.program, args.transcript)
        run_level1(args.transcript)
    elif level == '2':
        print_banner('l2', args.program, args.transcript)
        run_level2(args.transcript, waivers=waivers)
    elif level == '3':
        if os.path.exists(args.program_file):
            run_level3(args.transcript, args.program, args.program_file)
        else:
            print(f'{RD}Error:{RS} Program file required for Level 3 audit')
            sys.exit(1)
    elif level == 'full':
        if os.path.exists(args.program_file):
            run_full(args.transcript, args.program, args.program_file, waivers)
        else:
            print(f'{RD}Error:{RS} Program file required for full audit')
            sys.exit(1)


if __name__ == '__main__':
    main()
