"""
GradeTrace Core — Academic Transcript Audit Engine

Classes:
    CourseRecord       — single course attempt data model
    CourseCatalog      — NSU course database + prerequisites
    TranscriptParser   — CSV transcript parser
    CreditAuditor      — Level 1: credit tallying
    CGPAAuditor        — Level 2: CGPA + standing
    GraduationAuditor  — Level 3: graduation eligibility
    UnifiedAuditor     — combined pipeline + roadmap
"""

from packages.core.models import CourseRecord
from packages.core.course_catalog import CourseCatalog
from packages.core.transcript_parser import TranscriptParser
from packages.core.credit_engine import CreditAuditor
from packages.core.cgpa_engine import CGPAAuditor
from packages.core.audit_engine import GraduationAuditor
from packages.core.unified import UnifiedAuditor

__all__ = [
    "CourseRecord",
    "CourseCatalog",
    "TranscriptParser",
    "CreditAuditor",
    "CGPAAuditor",
    "GraduationAuditor",
    "UnifiedAuditor",
]
