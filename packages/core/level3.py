import pandas as pd
from packages.core.credit_engine import CreditAuditor
from packages.core.audit_engine import GraduationAuditor

def run_level3(df: pd.DataFrame, program: str) -> dict:
    """
    CSE226 Rubric Wrapper: Level 3 (Graduation Check).
    Accepts a pandas DataFrame and program string.
    Returns a dictionary of Level 3 results and roadmap.
    """
    rows = df.to_dict(orient="records")
    
    # Resolve retakes and calculate earned credits
    level1_data = CreditAuditor.process_rows(rows)
    records = level1_data["records"]
    earned = level1_data["credits_earned"]
    
    # Run Graduation Engine (assumes no specific concentration for raw wrapper)
    # The actual dict returned contains "eligible", "missing", "counts", and the roadmap.
    waivers = {}
    result = GraduationAuditor.audit(records, program, waivers, earned, level1_data.get("cgpa", 0.0))
    return result
