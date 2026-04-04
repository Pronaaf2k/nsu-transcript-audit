"""
mcp_server.py — MCP (Model Context Protocol) Server for NSU Transcript Audit

This server exposes audit functionality to AI agents via the MCP protocol.
Compatible with Claude Desktop, Cursor, and other MCP clients.

Usage:
    # Claude Desktop (add to claude_desktop_config.json):
    {
        "mcpServers": {
            "nsu-audit": {
                "command": "python",
                "args": ["F:/Github/nsu-transcript-audit/packages/api/mcp_server.py"]
            }
        }
    }
    
    # Cursor AI:
    # Add similar configuration to .cursor/mcp.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

MCP_VERSION = "2024-11-05"


def jsonrpc_response(result: Any, error: dict | None = None, request_id: int = 1) -> dict:
    if error:
        return {"jsonrpc": "2.0", "id": request_id, "error": error}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error(code: int, message: str, request_id: int = 1) -> dict:
    return jsonrpc_response(None, {"code": code, "message": message}, request_id)


def run_audit_from_csv(csv_text: str, program: str = "CSE") -> dict:
    """Run a full audit (L1, L2, L3) on CSV transcript data."""
    import csv
    import io
    
    from packages.core.unified import UnifiedAuditor
    
    reader = csv.DictReader(io.StringIO(csv_text))
    reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
    
    rows = []
    for r in reader:
        rows.append({
            "course_code": r.get("Course_Code", "").strip(),
            "course_name": r.get("Course_Name", "").strip(),
            "credits": r.get("Credits", "0").strip(),
            "grade": r.get("Grade", "").strip(),
            "semester": r.get("Semester", "").strip(),
            "section": ""
        })
    
    result = UnifiedAuditor.run_from_rows(rows, program, concentration=None)
    
    eligible = result.get("level_3", {}).get("eligible", False) if result.get("level_3") else False
    total_cr = result.get("level_1", {}).get("credits_earned", 0) if result.get("level_1") else 0
    cgpa = result.get("level_2", {}).get("cgpa", 0.0) if result.get("level_2") else 0.0
    
    return {
        "status": "success",
        "program": program,
        "total_credits": total_cr,
        "cgpa": cgpa,
        "graduation_status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "eligible": eligible,
        "level_1": result.get("level_1", {}),
        "level_2": result.get("level_2", {}),
        "level_3": result.get("level_3", {})
    }


def get_cgpa_breakdown(csv_text: str) -> dict:
    """Get detailed CGPA breakdown by semester."""
    import csv
    import io
    
    GRADE_POINTS = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0}
    
    reader = csv.DictReader(io.StringIO(csv_text))
    reader.fieldnames = [n.strip() for n in (reader.fieldnames or [])]
    
    semesters = {}
    for r in reader:
        sem = r.get("Semester", "Unknown").strip()
        if sem not in semesters:
            semesters[sem] = []
        semesters[sem].append({
            "course_code": r.get("Course_Code", "").strip(),
            "credits": float(r.get("Credits", 0) or 0),
            "grade": r.get("Grade", "").strip()
        })
    
    cumulative = {}
    results = []
    
    for sem in sorted(semesters.keys()):
        sem_rows = semesters[sem]
        sem_pts = 0
        sem_cred = 0
        
        for row in sem_rows:
            pts = GRADE_POINTS.get(row["grade"].upper(), None)
            if pts is not None and row["credits"] > 0:
                sem_pts += pts * row["credits"]
                sem_cred += row["credits"]
                
                code = row["course_code"]
                if code not in cumulative:
                    cumulative[code] = {"points": pts, "credits": row["credits"]}
                elif pts > cumulative[code]["points"]:
                    cumulative[code] = {"points": pts, "credits": row["credits"]}
        
        tgpa = int((sem_pts / sem_cred if sem_cred > 0 else 0) * 100) / 100
        total_pts = sum(d["points"] * d["credits"] for d in cumulative.values())
        total_cred = sum(d["credits"] for d in cumulative.values())
        cgpa = int((total_pts / total_cred if total_cred > 0 else 0) * 100) / 100
        
        results.append({
            "semester": sem,
            "tgpa": tgpa,
            "cgpa": cgpa,
            "credits": sem_cred,
            "courses": len(sem_rows)
        })
    
    return {
        "status": "success",
        "semesters": results,
        "final_cgpa": results[-1]["cgpa"] if results else 0,
        "total_credits": sum(s["credits"] for s in results)
    }


def check_missing_courses(csv_text: str, program: str = "CSE") -> dict:
    """Check which required courses are missing for graduation."""
    from packages.cli.audit.audit_l3 import parse_program_knowledge, audit_student
    
    program_file = ROOT_DIR / "packages" / "cli" / "program.md"
    if not program_file.exists():
        program_file = ROOT_DIR / "program.md"
    
    full_name = {
        "CSE": "Computer Science & Engineering",
        "BBA": "Business Administration",
        "ETE": "Electronic & Telecom Engineering",
        "ENV": "Environmental Science & Management",
        "ENG": "English",
        "ECO": "Economics",
    }.get(program.upper(), program)
    
    if not program_file.exists():
        return {"status": "error", "message": "Program file not found"}
    
    requirements = parse_program_knowledge(str(program_file), full_name)
    result = audit_student(csv_text, requirements, md_file=str(program_file))
    
    return {
        "status": "success",
        "program": program,
        "missing": result["missing"],
        "invalid_electives": result["invalid_electives"],
        "advisories": result["advisories"],
        "total_earned": result["total_earned"],
        "required": requirements["total_credits_required"]
    }


def get_audit_history(limit: int = 10) -> dict:
    from packages.api.local_storage import get_audit_history as get_history
    try:
        history = get_history(limit=limit)
        return {"status": "success", "audits": history}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_audit_by_id(audit_id: str) -> dict:
    from packages.api.local_storage import get_audit as get_audit_local
    try:
        audit = get_audit_local(audit_id)
        if not audit:
            return {"status": "error", "message": "Audit not found"}
        return {"status": "success", "audit": audit}
    except Exception as e:
        return {"status": "error", "message": str(e)}


TOOLS = {
    "audit_run": {
        "description": "Run a full L1/L2/L3 audit on a CSV transcript",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"},
                "program": {"type": "string", "description": "Program code (CSE, BBA, ETE, ENV, ENG, ECO)", "default": "CSE"}
            },
            "required": ["csv_text"]
        }
    },
    "cgpa_breakdown": {
        "description": "Get semester-by-semester CGPA breakdown",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"}
            },
            "required": ["csv_text"]
        }
    },
    "check_missing": {
        "description": "Check which required courses are missing for graduation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_text": {"type": "string", "description": "CSV content with columns: Course_Code, Course_Name, Credits, Grade, Semester"},
                "program": {"type": "string", "description": "Program code (CSE, BBA, ETE, ENV, ENG, ECO)", "default": "CSE"}
            },
            "required": ["csv_text"]
        }
    },
    "history_list": {
        "description": "Get recent audit history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "description": "Maximum number of results", "default": 10}
            }
        }
    },
    "history_get": {
        "description": "Get a specific audit by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "audit_id": {"type": "string", "description": "The audit ID to retrieve"}
            },
            "required": ["audit_id"]
        }
    }
}


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    if tool_name == "audit_run":
        return run_audit_from_csv(arguments["csv_text"], arguments.get("program", "CSE"))
    elif tool_name == "cgpa_breakdown":
        return get_cgpa_breakdown(arguments["csv_text"])
    elif tool_name == "check_missing":
        return check_missing_courses(arguments["csv_text"], arguments.get("program", "CSE"))
    elif tool_name == "history_list":
        return get_audit_history(arguments.get("limit", 10))
    elif tool_name == "history_get":
        return get_audit_by_id(arguments["audit_id"])
    else:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 1)
    
    if method == "initialize":
        return jsonrpc_response({
            "protocolVersion": MCP_VERSION,
            "serverInfo": {"name": "nsu-audit", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": True}}
        }, request_id=request_id)
    
    elif method == "tools/list":
        tools_list = []
        for name, spec in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return jsonrpc_response({"tools": tools_list}, request_id=request_id)
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in TOOLS:
            return jsonrpc_error(-32601, f"Unknown tool: {tool_name}", request_id)
        
        try:
            result = handle_tool_call(tool_name, arguments)
            return jsonrpc_response({
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            }, request_id=request_id)
        except Exception as e:
            return jsonrpc_error(-32603, f"Tool error: {str(e)}", request_id)
    
    elif method == "ping":
        return jsonrpc_response({"pong": True}, request_id=request_id)
    
    else:
        return jsonrpc_error(-32601, f"Method not found: {method}", request_id)


def main():
    print("NSU Audit MCP Server starting...", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps(jsonrpc_error(-32700, f"Parse error: {str(e)}")), flush=True)
        except Exception as e:
            print(json.dumps(jsonrpc_error(-32603, f"Server error: {str(e)}")), flush=True)


if __name__ == "__main__":
    main()
