from mcp.server.fastmcp import FastMCP
import sys
import os

from packages.api.main import _run_audit
from packages.api.supabase_client import save_transcript_and_audit

mcp = FastMCP("nsu-audit")

@mcp.tool()
def run_audit(transcript_csv: str, program: str, level: int = 3) -> dict:
    """
    Run an NSU graduation audit on a CSV transcript.
    Args:
        transcript_csv: Multiline string containing CSV format (Course_Code,Credits,Grade,Semester,Attempt)
        program: The 3-letter program code (e.g. CSE, BBA)
        level: Audit level (1: credit tally, 2: cgpa, 3: full audit)
    """
    result = _run_audit(transcript_csv, program)
    # The _run_audit function internally runs all 3 levels and saves it to DB
    
    # Return the specific level requested, or everything
    if level == 1:
        return result.get("l1", {})
    elif level == 2:
        return result.get("l2", {})
    else:
        return result
        
if __name__ == "__main__":
    mcp.run()
