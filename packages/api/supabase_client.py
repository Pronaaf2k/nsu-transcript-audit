import os
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = type('MockClient', (), {})

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

supabase: Client | None = None
if HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Warning: Failed to init Supabase client: {e}")

def save_transcript_and_audit(csv_text: str, program: str, level: int, audit_result: dict, student_id: str | None = None):
    if not supabase:
        return
    try:
        import csv
        import io
        import json
        
        # 1. Insert extracted rows into transcripts table
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = []
        for line in reader:
            rows.append({
                "student_id": student_id,
                "course": line.get("Course_Code", "").strip(),
                "credits": float(line.get("Credits", 0) or 0),
                "grade": line.get("Grade", "").strip(),
                "semester": line.get("Semester", "").strip()
            })
        if rows:
            supabase.table("transcripts").insert(rows).execute()
        
        # 2. Insert into audit_results
        cgpa = audit_result.get("cgpa", 0.0)
        eligible = audit_result.get("graduation_status") == "PASS"
        missing = audit_result.get("l3", {}).get("missing_courses", [])
        advisories = audit_result.get("l3", {}).get("advisories", [])
        
        supabase.table("audit_results").insert({
            "student_id": student_id,
            "program": program,
            "audit_level": level,
            "cgpa": cgpa,
            "eligible": eligible,
            "missing_courses": missing,
            "advisories": advisories
        }).execute()

    except Exception as e:
        print(f"Error saving to Supabase: {e}")
