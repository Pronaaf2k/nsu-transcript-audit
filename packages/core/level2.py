import pandas as pd
from packages.core.credit_engine import CreditAuditor
from packages.core.cgpa_engine import CGPAAuditor

def run_level2(df: pd.DataFrame, program: str) -> dict:
    """
    CSE226 Rubric Wrapper: Level 2 (CGPA & Probation).
    Accepts a pandas DataFrame and program string.
    Returns a dictionary of Level 2 results.
    """
    rows = df.to_dict(orient="records")
    
    # Must run Level 1 first to resolve retakes
    level1_data = CreditAuditor.process_rows(rows)
    records = level1_data["records"]
    
    # Run the CGPA Engine
    return CGPAAuditor.process(records, program=program)
