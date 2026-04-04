import pandas as pd
from packages.core.credit_engine import CreditAuditor

def run_level1(df: pd.DataFrame, program: str) -> dict:
    """
    CSE226 Rubric Wrapper: Level 1 (Credit Tallying).
    Accepts a pandas DataFrame and program string.
    Returns a dictionary of Level 1 audit results.
    """
    # Convert DataFrame to standard list of dicts for our engine
    rows = df.to_dict(orient="records")
    
    # Run our robust Credit Engine
    level1_result = CreditAuditor.process_rows(rows)
    
    # Optional: ensure records are easily serializable dictionaries
    if "records" in level1_result:
        # FastAPI handles dataclasses, but for pure dict return, we convert them
        import dataclasses
        level1_result["records"] = [dataclasses.asdict(r) for r in level1_result["records"]]
        
    # Unrecognized set to list for JSON serialization
    if "unrecognized" in level1_result:
        level1_result["unrecognized"] = list(level1_result["unrecognized"])
        
    return level1_result
