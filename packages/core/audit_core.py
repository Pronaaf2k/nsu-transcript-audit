import pandas as pd
from packages.core.unified import UnifiedAuditor

def run_full_audit(df: pd.DataFrame, program: str) -> dict:
    """
    CSE226 Rubric Wrapper: Full Unified Audit.
    Accepts a pandas DataFrame and program string.
    Returns the complete structured JSON representation of the transcript audit.
    """
    rows = df.to_dict(orient="records")
    
    # Run full integrated pipeline
    result = UnifiedAuditor.run_from_rows(rows, program)
    return result
