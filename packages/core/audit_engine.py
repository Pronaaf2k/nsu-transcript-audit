"""
GradeTrace Core — Graduation Auditor (Level 3)

Compares passed courses against program requirements, identifies remaining
courses, checks prerequisites, and determines graduation eligibility.

Ported from engine/audit_engine.py — algorithms unchanged.
"""

import collections

from packages.core.models import CourseRecord, SEMESTERS
from packages.core.cgpa_engine import CGPAAuditor
from packages.core.course_catalog import CourseCatalog


class GraduationAuditor:
    """Level 3 — Audit & Graduation Eligibility Engine."""

    # ───────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────

    @staticmethod
    def _get_passed_courses(records: list[CourseRecord]) -> set[str]:
        """Return set of course codes the student has passed."""
        return {r.course_code for r in records
                if r.status in ("BEST", "WAIVED") and r.grade not in ("F", "I", "W")}

    @staticmethod
    def _find_missing(required_dict: dict, passed_set: set) -> dict:
        """Return {course: credits} for courses not yet passed."""
        return {c: cr for c, cr in required_dict.items() if c not in passed_set}

    @staticmethod
    def _check_choice_group(choice_dict: dict, passed_set: set) -> dict:
        """Check if at least one course from a choice group is passed."""
        for c in choice_dict:
            if c in passed_set:
                return {}
        return choice_dict

    # ───────────────────────────────────────────────
    # Prerequisite Violations
    # ───────────────────────────────────────────────

    @staticmethod
    def check_prerequisite_violations(program: str, records: list[CourseRecord],
                                      waivers: dict) -> list[dict]:
        """
        Check if courses were taken before their prerequisites were passed.
        Returns list of dicts: {"course", "semester", "missing"}.
        """
        sem_map = {sem: i for i, sem in enumerate(SEMESTERS)}
        records_by_sem = collections.defaultdict(list)
        for r in records:
            records_by_sem[r.semester].append(r)

        sorted_sems = sorted(records_by_sem.keys(), key=lambda s: sem_map.get(s, 9999))

        prereq_map = CourseCatalog.get_prerequisites(program)
        passed_so_far = set(k for k, v in waivers.items() if v)
        violations = []
        credits_at_step = 0
        first_sem = sorted_sems[0] if sorted_sems else None

        for current_sem in sorted_sems:
            sem_records = records_by_sem[current_sem]

            # First semester exception: concurrent enrollment allowed
            if current_sem == first_sem:
                for r in sem_records:
                    if r.grade not in ("F", "W", "I"):
                        passed_so_far.add(r.course_code)
                        credits_at_step += r.credits

            for r in sem_records:
                code = r.course_code
                if code in prereq_map:
                    required = prereq_map[code]
                    missing = []
                    for req in required:
                        if req == "_SENIOR_":
                            if credits_at_step < 100:
                                missing.append("Senior Status (100+ Credits)")
                        elif req not in passed_so_far:
                            missing.append(req)
                    if missing:
                        violations.append({
                            "course": code,
                            "semester": current_sem,
                            "missing": missing,
                        })

            if current_sem != first_sem:
                for r in sem_records:
                    if r.grade not in ("F", "W", "I"):
                        passed_so_far.add(r.course_code)
                        credits_at_step += r.credits

        return violations

    # ───────────────────────────────────────────────
    # CSE Audit
    # ───────────────────────────────────────────────

    @staticmethod
    def _audit_cse(records: list[CourseRecord], waivers: dict,
                   credits_earned: int, cgpa: float, credit_reduction: int = 0) -> dict:
        """Perform CSE program audit (130-credit curriculum)."""
        C = CourseCatalog
        passed = GraduationAuditor._get_passed_courses(records)
        remaining = {}
        reasons = []
        total_required = C.CSE_TOTAL_CREDITS - credit_reduction

        # CSE Major Core
        missing_core = GraduationAuditor._find_missing(C.CSE_MAJOR_CORE, passed)
        if missing_core:
            remaining["CSE Major Core"] = missing_core

        # Capstone
        missing_cap = GraduationAuditor._find_missing(C.CSE_CAPSTONE, passed)
        if missing_cap:
            remaining["Capstone"] = missing_cap

        # SEPS Core
        missing_seps = GraduationAuditor._find_missing(C.CSE_SEPS_CORE, passed)
        if missing_seps:
            remaining["SEPS Core"] = missing_seps

        # GED required
        missing_ged = GraduationAuditor._find_missing(C.CSE_GED_REQUIRED, passed)
        if missing_ged:
            remaining["GED Required"] = missing_ged

        # GED choice groups
        missing_c1 = GraduationAuditor._check_choice_group(C.CSE_GED_CHOICE_1, passed)
        if missing_c1:
            remaining["GED Choice (ECO101 or ECO104)"] = missing_c1

        missing_c2 = GraduationAuditor._check_choice_group(C.CSE_GED_CHOICE_2, passed)
        if missing_c2:
            remaining["GED Choice (POL101 or POL104)"] = missing_c2

        missing_c3 = GraduationAuditor._check_choice_group(C.CSE_GED_CHOICE_3, passed)
        if missing_c3:
            remaining["GED Choice (SOC101/ANT101/ENV203/GEO205)"] = missing_c3

        # Waivable courses
        waivable_remaining = {}
        for course, cr in C.CSE_GED_WAIVABLE.items():
            if not waivers.get(course, False) and course not in passed:
                waivable_remaining[course] = cr
        if waivable_remaining:
            remaining["Waivable Courses"] = waivable_remaining

        # CSE 400-level electives
        cse_400_electives = [c for c in passed
                             if c.startswith("CSE4") and c not in C.CSE_MAJOR_CORE and c not in C.CSE_CAPSTONE]
        elective_credits = sum(3 for _ in cse_400_electives)
        if elective_credits < C.CSE_ELECTIVE_CREDITS:
            needed = (C.CSE_ELECTIVE_CREDITS - elective_credits) // 3
            remaining["CSE Electives (400-level)"] = {
                f"Any CSE 4xx ({needed} needed)": C.CSE_ELECTIVE_CREDITS - elective_credits
            }

        # Open electives
        all_required_codes = (
            set(C.CSE_ALL_CORE.keys()) | set(C.CSE_CAPSTONE.keys()) |
            set(C.CSE_GED_REQUIRED.keys()) | set(C.CSE_GED_CHOICE_1.keys()) |
            set(C.CSE_GED_CHOICE_2.keys()) | set(C.CSE_GED_CHOICE_3.keys()) |
            set(C.CSE_GED_WAIVABLE.keys())
        )
        counted_open = set()
        open_elec_credits = 0
        for r in records:
            if (r.course_code not in all_required_codes and
                r.course_code not in counted_open and
                not (r.course_code.startswith("CSE4") and
                     r.course_code not in C.CSE_MAJOR_CORE and
                     r.course_code not in C.CSE_CAPSTONE) and
                r.status in ("BEST", "WAIVED") and r.credits > 0 and
                r.grade not in ("F", "I", "W")):
                open_elec_credits += r.credits
                counted_open.add(r.course_code)

        if open_elec_credits < C.CSE_OPEN_ELECTIVE_CREDITS:
            needed_cr = C.CSE_OPEN_ELECTIVE_CREDITS - open_elec_credits
            remaining["Open Electives"] = {f"Any courses ({needed_cr} credits needed)": needed_cr}

        # Major CGPAs
        major_core_cgpa = CGPAAuditor.compute_major_cgpa(records, list(C.CSE_MAJOR_CORE.keys()))
        elective_codes = [c for c in passed
                          if c.startswith("CSE4") and c not in C.CSE_MAJOR_CORE and c not in C.CSE_CAPSTONE]
        major_elective_cgpa = CGPAAuditor.compute_major_cgpa(records, elective_codes) if elective_codes else 0.0

        # Eligibility
        eligible = True

        if credits_earned < total_required:
            eligible = False
            reasons.append(f"Credits earned ({credits_earned}) < {total_required} required")

        if cgpa < C.CSE_MIN_CGPA:
            eligible = False
            reasons.append(f"Overall CGPA ({cgpa:.2f}) < {C.CSE_MIN_CGPA:.2f}")

        if major_core_cgpa < C.CSE_MAJOR_CORE_CGPA:
            eligible = False
            reasons.append(f"Major Core CGPA ({major_core_cgpa:.2f}) < {C.CSE_MAJOR_CORE_CGPA:.2f}")

        if elective_codes and major_elective_cgpa < C.CSE_MAJOR_ELECTIVE_CGPA:
            eligible = False
            reasons.append(f"Major Elective CGPA ({major_elective_cgpa:.2f}) < {C.CSE_MAJOR_ELECTIVE_CGPA:.2f}")

        for r in records:
            if r.status == "UNAUTHORIZED-RETAKE":
                eligible = False
                reasons.append(f"Invalid course: Unauthorized retake of {r.course_code} ({r.grade} in {r.semester})")

        if remaining:
            eligible = False
            total_missing = sum(len(v) for v in remaining.values())
            reasons.append(f"{total_missing} required course(s) still missing")

        result = {
            "eligible": eligible,
            "reasons": reasons,
            "remaining": remaining,
            "major_core_cgpa": major_core_cgpa,
            "major_elective_cgpa": major_elective_cgpa,
            "total_credits_required": total_required,
        }
        result["prereq_violations"] = GraduationAuditor.check_prerequisite_violations("CSE", records, waivers)
        return result

    # ───────────────────────────────────────────────
    # BBA Audit
    # ───────────────────────────────────────────────

    @staticmethod
    def _audit_bba(records: list[CourseRecord], waivers: dict,
                   credits_earned: int, cgpa: float,
                   credit_reduction: int = 0, concentration: str | None = None) -> dict:
        """Perform BBA program audit — Curriculum 143+."""
        C = CourseCatalog
        passed = GraduationAuditor._get_passed_courses(records)
        remaining = {}
        reasons = []
        total_required = C.BBA_TOTAL_CREDITS - credit_reduction

        if not concentration:
            reasons.append("Major/Concentration not yet declared")

        # School Core
        missing_school = GraduationAuditor._find_missing(C.BBA_SCHOOL_CORE, passed)
        if missing_school:
            remaining["School Core"] = missing_school

        # BBA Core
        missing_core = GraduationAuditor._find_missing(C.BBA_CORE, passed)
        if missing_core:
            remaining["BBA Core"] = missing_core

        # GED fixed
        missing_ged = GraduationAuditor._find_missing(C.BBA_GED, passed)
        if missing_ged:
            remaining["GED"] = missing_ged

        # GED Choice: Language
        missing_lang = GraduationAuditor._check_choice_group(C.BBA_GED_CHOICE_LANG, passed)
        if missing_lang:
            remaining["GED Choice (Language)"] = missing_lang

        # GED Choice: History (pick 2)
        his_passed = [c for c in C.BBA_GED_CHOICE_HIS if c in passed]
        his_needed = 2 - len(his_passed)
        if his_needed > 0:
            his_options = {c: cr for c, cr in C.BBA_GED_CHOICE_HIS.items() if c not in passed}
            remaining[f"GED Choice (History, pick {his_needed})"] = his_options

        # GED Choice: Political Science
        missing_pol = GraduationAuditor._check_choice_group(C.BBA_GED_CHOICE_POL, passed)
        if missing_pol:
            remaining["GED Choice (Political Science)"] = missing_pol

        # GED Choice: Social Science
        missing_soc = GraduationAuditor._check_choice_group(C.BBA_GED_CHOICE_SOC, passed)
        if missing_soc:
            remaining["GED Choice (Social Science)"] = missing_soc

        # GED Choice: Science (pick 3)
        sci_passed = [c for c in C.BBA_GED_CHOICE_SCI if c in passed]
        sci_needed = 3 - len(sci_passed)
        if sci_needed > 0:
            sci_options = {c: cr for c, cr in C.BBA_GED_CHOICE_SCI.items() if c not in passed}
            remaining[f"GED Choice (Science, pick {sci_needed})"] = sci_options

        # GED Choice: Lab
        lab_passed = [c for c in C.BBA_GED_CHOICE_LAB if c in passed]
        if len(lab_passed) == 0:
            remaining["GED Choice (Lab)"] = dict(C.BBA_GED_CHOICE_LAB)

        # Waivable courses
        waivable_remaining = {}
        for course, cr in C.BBA_GED_WAIVABLE.items():
            if not waivers.get(course, False) and course not in passed:
                waivable_remaining[course] = cr
        if waivable_remaining:
            remaining["GED Waivable"] = waivable_remaining

        # Internship
        missing_intern = GraduationAuditor._find_missing(C.BBA_INTERNSHIP, passed)
        if missing_intern:
            remaining["Internship"] = missing_intern

        # Concentration courses (18cr)
        conc_label = "Undeclared"
        conc_all_codes = []
        if concentration and concentration.upper() in C.BBA_CONCENTRATIONS:
            conc_key = concentration.upper()
            conc_req, conc_elec, conc_label = C.BBA_CONCENTRATIONS[conc_key]

            missing_conc_req = GraduationAuditor._find_missing(conc_req, passed)
            if missing_conc_req:
                remaining[f"{conc_label} Required"] = missing_conc_req

            elec_passed = [c for c in conc_elec if c in passed]
            elec_needed = 2 - len(elec_passed)
            if elec_needed > 0:
                elec_options = {c: cr for c, cr in conc_elec.items() if c not in passed}
                remaining[f"{conc_label} Elective (pick {elec_needed})"] = elec_options

            conc_all_codes = list(conc_req.keys()) + [c for c in conc_elec if c in passed]

        # Free Electives (9cr)
        conc_code_set = set(conc_all_codes)
        all_required_codes = (
            set(C.BBA_SCHOOL_CORE.keys()) | set(C.BBA_CORE.keys()) |
            set(C.BBA_GED.keys()) | set(C.BBA_GED_CHOICE_LANG.keys()) |
            set(C.BBA_GED_CHOICE_HIS.keys()) | set(C.BBA_GED_CHOICE_POL.keys()) |
            set(C.BBA_GED_CHOICE_SOC.keys()) | set(C.BBA_GED_CHOICE_SCI.keys()) |
            set(C.BBA_GED_CHOICE_LAB.keys()) | set(C.BBA_GED_WAIVABLE.keys()) |
            set(C.BBA_INTERNSHIP.keys()) | conc_code_set
        )
        counted_open = set()
        free_elec_credits = 0
        for r in records:
            if (r.course_code not in all_required_codes and
                r.course_code not in counted_open and
                r.status in ("BEST", "WAIVED") and r.credits > 0 and
                r.grade not in ("F", "I", "W")):
                free_elec_credits += r.credits
                counted_open.add(r.course_code)

        if free_elec_credits < C.BBA_FREE_ELECTIVE_CREDITS:
            needed_cr = C.BBA_FREE_ELECTIVE_CREDITS - free_elec_credits
            remaining["Free Electives"] = {f"Any courses ({needed_cr} credits needed)": needed_cr}

        # CGPAs
        core_codes = list(C.BBA_ALL_CORE.keys())
        core_cgpa = CGPAAuditor.compute_major_cgpa(records, core_codes)
        concentration_cgpa = (
            CGPAAuditor.compute_major_cgpa(records, conc_all_codes) if conc_all_codes
            else core_cgpa
        )

        # Eligibility
        eligible = True

        if credits_earned < total_required:
            eligible = False
            reasons.append(f"Credits earned ({credits_earned}) < {total_required} required")

        if cgpa < C.BBA_MIN_CGPA:
            eligible = False
            reasons.append(f"Overall CGPA ({cgpa:.2f}) < {C.BBA_MIN_CGPA:.2f}")

        if core_cgpa < C.BBA_CORE_CGPA:
            eligible = False
            reasons.append(f"School & BBA Core CGPA ({core_cgpa:.2f}) < {C.BBA_CORE_CGPA:.2f}")

        if concentration_cgpa < C.BBA_CONCENTRATION_CGPA:
            eligible = False
            reasons.append(f"Concentration CGPA ({concentration_cgpa:.2f}) < {C.BBA_CONCENTRATION_CGPA:.2f}")

        for r in records:
            if r.status == "UNAUTHORIZED-RETAKE":
                eligible = False
                reasons.append(f"Invalid course: Unauthorized retake of {r.course_code} ({r.grade} in {r.semester})")

        if remaining:
            eligible = False
            total_missing = sum(len(v) for v in remaining.values())
            reasons.append(f"{total_missing} required course(s) still missing")

        result = {
            "eligible": eligible,
            "reasons": reasons,
            "remaining": remaining,
            "core_cgpa": core_cgpa,
            "concentration_cgpa": concentration_cgpa,
            "concentration_label": conc_label,
            "total_credits_required": total_required,
        }
        result["prereq_violations"] = GraduationAuditor.check_prerequisite_violations("BBA", records, waivers)
        return result

    # ───────────────────────────────────────────────
    # Graduation Roadmap
    # ───────────────────────────────────────────────

    @staticmethod
    def build_graduation_roadmap(program: str, records: list[CourseRecord],
                                 credits_earned: int, cgpa: float, major_cgpa: float,
                                 audit_result: dict, standing: str) -> dict:
        """Build an actionable graduation roadmap."""
        total_req = audit_result["total_credits_required"]
        remaining = audit_result.get("remaining", {})
        eligible = audit_result["eligible"]

        roadmap = {
            "eligible": eligible,
            "steps": [],
            "credit_gap": 0,
            "missing_course_credits": 0,
            "estimated_courses_left": 0,
            "estimated_semesters": 0,
        }

        if eligible:
            roadmap["steps"].append({
                "category": "CONGRATULATIONS",
                "action": "You have met all graduation requirements!",
                "priority": "DONE",
                "detail": None,
            })
            return roadmap

        # Credit gap
        if credits_earned < total_req:
            gap = total_req - credits_earned
            roadmap["credit_gap"] = gap
            roadmap["steps"].append({
                "category": "CREDITS",
                "action": f"Earn {gap} more credits to reach the {total_req}-credit requirement",
                "priority": "HIGH",
                "detail": f"Currently at {credits_earned}/{total_req} credits.",
            })

        # CGPA improvement
        min_cgpa = 2.0
        if cgpa < min_cgpa:
            if "P2" in standing:
                detail = f"CRITICAL: You are on {standing}. This is your LAST consecutive semester on probation. Failure to reach 2.0 CGPA will lead to automatic dismissal."
            elif "DISMISSAL" in standing:
                detail = f"CAUTION: You have exceeded the probation limit. You are at dismissal stage. Contact Academic Advising immediately."
            else:
                detail = f"You are on {standing}. Focus on higher grades in remaining courses. Retaking low-grade courses may help."

            roadmap["steps"].append({
                "category": "CGPA",
                "action": f"Raise overall CGPA from {cgpa:.2f} to at least {min_cgpa:.2f}",
                "priority": "CRITICAL",
                "detail": detail,
            })

        # Major/Core CGPA
        major_threshold = 2.0
        major_label = "Major CGPA" if program.upper() == "CSE" else "Core GPA"
        if major_cgpa < major_threshold:
            roadmap["steps"].append({
                "category": "MAJOR GPA",
                "action": f"Raise {major_label} from {major_cgpa:.2f} to at least {major_threshold:.2f}",
                "priority": "HIGH",
                "detail": "Consider retaking core courses where you scored D/D+ to improve this.",
            })

        # Undeclared Major (BBA)
        if program.upper() == "BBA" and audit_result.get("concentration_label") == "Undeclared":
            prio = "CRITICAL" if credits_earned >= 60 else "LOW"
            roadmap["steps"].append({
                "category": "DECLARE MAJOR",
                "action": "Select and declare your Concentration/Major area",
                "priority": prio,
                "detail": (
                    f"You have {credits_earned} credits. " +
                    ("It is critical to declare now to start major courses."
                     if credits_earned >= 60 else
                     "You should focus on core credits, but start thinking about your major.")
                ),
            })

        # Missing courses
        total_missing_courses = 0
        total_missing_credits = 0
        for category, courses in remaining.items():
            course_list = list(courses.items())
            cat_credits = sum(cr for _, cr in course_list)
            total_missing_courses += len(course_list)
            total_missing_credits += cat_credits

            if "Choice" in category:
                options = " or ".join(c for c, _ in course_list)
                roadmap["steps"].append({
                    "category": category.upper(),
                    "action": f"Complete 1 course from: {options}",
                    "priority": "MEDIUM",
                    "detail": f"Pick any one ({cat_credits} credits each).",
                })
            elif "Elective" in category or "Open" in category:
                roadmap["steps"].append({
                    "category": category.upper(),
                    "action": f"Complete {cat_credits} credits of electives",
                    "priority": "MEDIUM",
                    "detail": ", ".join(f"{c} ({cr}cr)" for c, cr in course_list),
                })
            elif "Waivable" in category:
                roadmap["steps"].append({
                    "category": category.upper(),
                    "action": f"Pass or get waiver for: {', '.join(c for c, _ in course_list)}",
                    "priority": "LOW",
                    "detail": "0-credit course - does not affect CGPA or credit total, but is required.",
                })
            else:
                roadmap["steps"].append({
                    "category": category.upper(),
                    "action": f"Complete {len(course_list)} course(s) ({cat_credits} credits)",
                    "priority": "HIGH",
                    "detail": ", ".join(f"{c} ({cr}cr)" for c, cr in course_list),
                })

        roadmap["missing_course_credits"] = total_missing_credits
        roadmap["estimated_courses_left"] = total_missing_courses

        # Estimate semesters
        credits_still_needed = max(roadmap["credit_gap"], total_missing_credits)
        if credits_still_needed > 0:
            roadmap["estimated_semesters"] = max(1, -(-credits_still_needed // 15))
        else:
            roadmap["estimated_semesters"] = 1 if not eligible else 0

        # Retake recommendations
        if cgpa < min_cgpa or major_cgpa < major_threshold:
            low_grade_courses = []
            seen = set()
            for r in records:
                if (r.status == "BEST" and r.grade in ("D", "D+", "C-") and
                    r.credits > 0 and r.course_code not in seen):
                    low_grade_courses.append((r.course_code, r.grade, r.credits))
                    seen.add(r.course_code)

            if low_grade_courses:
                low_grade_courses.sort(key=lambda x: -x[2])
                top_retakes = low_grade_courses[:5]
                detail = ", ".join(f"{c} (current: {g}, {cr}cr)" for c, g, cr in top_retakes)
                roadmap["steps"].append({
                    "category": "RETAKE SUGGESTIONS",
                    "action": f"Consider retaking {len(top_retakes)} course(s) to boost GPA",
                    "priority": "RECOMMENDED",
                    "detail": detail,
                })

        return roadmap

    # ───────────────────────────────────────────────
    # Audit Dispatcher
    # ───────────────────────────────────────────────

    @staticmethod
    def audit(records: list[CourseRecord], program: str, waivers: dict,
              credits_earned: int, cgpa: float, credit_reduction: int = 0,
              concentration: str | None = None) -> dict:
        """Dispatch to the correct program audit."""
        if program.upper() == "CSE":
            return GraduationAuditor._audit_cse(records, waivers, credits_earned, cgpa, credit_reduction)
        elif program.upper() == "BBA":
            return GraduationAuditor._audit_bba(records, waivers, credits_earned, cgpa, credit_reduction, concentration)
        else:
            raise ValueError(f"Unknown program: {program}. Use 'CSE' or 'BBA'.")
