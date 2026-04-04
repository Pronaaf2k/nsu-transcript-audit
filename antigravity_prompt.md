# NSU Graduation Audit System — Build Instructions

## Context

I have an NSU Graduation Audit System. The frontend is a single HTML file (`nsu_audit.html`) that accepts CSV transcript input and calls the Anthropic Claude API to run a 3-level graduation audit. I have a PostgreSQL database already set up. Build the full backend pipeline described below.

---

## What to Build

### 1. PDF Upload & OCR

Replace the CSV textarea in `nsu_audit.html` with a PDF upload button. When a student uploads their NSU transcript PDF:

- Send it to the Claude API as a base64 document
- Extract the course table into this JSON format:

```json
[
  { "course": "CSE115", "credits": 4, "grade": "A", "semester": "Spring 2022" },
  { "course": "ENG102", "credits": 3, "grade": "B+", "semester": "Spring 2022" }
]
```

- Show the extracted courses to the user for review before running the audit

---

### 2. PostgreSQL Storage

Store the following after OCR and after audit:

**Transcripts table** — raw extracted rows:
- student_id (if available in PDF), course, credits, grade, semester, created_at

**Audit results table** — one row per audit run:
- student_id, program, level, cgpa, eligible, missing_courses (JSON), advisories (JSON), timestamp

---

### 3. Run Audit & Show Results

After extraction, run the audit using the existing logic in `nsu_audit.html` (see `buildSystemPrompt()` and `renderResult()` functions) and display results in the existing UI.

---

### 4. MCP Endpoint

Expose the audit engine as an MCP (Model Context Protocol) server with one tool:

```
run_audit(transcript_csv: string, program: string, level: 1 | 2 | 3) → audit result JSON
```

---

## Tech Constraints

- Backend: Node.js/Express or Python/FastAPI
- Database: PostgreSQL (already set up)
- Claude API model: `claude-sonnet-4-20250514`
- Send PDFs as base64 with `type: "document"` in the API request
- The HTML file must call the backend instead of the Anthropic API directly — keep the API key server-side
