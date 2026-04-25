# NSU Transcript Audit

A full-stack graduation audit system for North South University (NSU) students. Audit your transcript to check graduation eligibility, view CGPA, and identify missing courses.

## Live Links

| Service | URL |
|---------|-----|
| **Web App** (Vercel) | https://nsu-transcript-audit.vercel.app |
| **Backend API** (Render) | https://nsu-transcript-audit.onrender.com |
| **API Docs** | https://nsu-transcript-audit.onrender.com/docs |
| **Supabase** | https://supabase.com/dashboard/project/imamqcvlmfkcbthxuxsq |

## Features

- **CSV Upload** - Upload your transcript as CSV for instant audit
- **OCR Scan** - Upload PDF/image transcripts for AI-powered extraction
- **Semester View** - View grades organized by semester with TGPA
- **Graduation Audit** - Check eligibility against program requirements
- **Export Options** - Download results as CSV or JSON

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │   Render        │     │   Supabase     │
│   (Frontend)    │ ──► │   (Backend)     │ ──► │   (Database)   │
│   Next.js 14    │     │   FastAPI       │     │   PostgreSQL   │
│                 │     │   + Gemini      │     │                │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Frontend (Vercel)
- Next.js 14 with TypeScript
- Supabase Auth (Google OAuth)
- Browser-based audit engine
- Responsive dark theme UI

### Backend (Render)
- FastAPI with Python 3.11
- Gemini 2.5 Flash Lite for OCR
- L1/L2/L3 audit engine
- CORS enabled for frontend

### Database (Supabase)
- `transcript_scans` - Upload history
- `audit_results` - Audit results with RLS
- Row-Level Security for user data

## Tech Stack

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11, Gemini AI
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Vercel, Render

## Getting Started

### Prerequisites
- Git
- Node.js 20+
- pnpm 9+
- Python 3.11+ (`py` launcher on Windows)
- PowerShell 5.1+
- Supabase account
- Gemini API key

### Fresh Device Setup (Windows PowerShell)

Use these exact commands on a brand-new machine:

```powershell
git clone https://github.com/Pronaaf2k/nsu-transcript-audit.git
cd nsu-transcript-audit
Copy-Item .env.example .env
# edit .env and fill all required values before continuing
pnpm setup:local
pnpm dev:local
```

This starts:
- Web app: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

Important: this repo uses a single root `.env` for local runs (`pnpm cli`, `pnpm web`, `pnpm dev:mobile`, `pnpm dev:local`).

### Required Environment Variables (`.env` at repo root)

Start from `.env.example` and set these values:

```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...
SUPABASE_SERVICE_ROLE_KEY=...            # optional for server-side writes

GEMINI_API_KEY=...

NEXT_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_API_URL=http://localhost:8000
GRADGATE_API_URL=http://localhost:8000

NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...

EXPO_PUBLIC_SUPABASE_URL=...
EXPO_PUBLIC_SUPABASE_ANON_KEY=...
```

### Day-to-Day Run Commands (from repo root)

- Start web + API together (recommended):

```powershell
pnpm dev:local
```

- Start web only (auto-starts API if needed):

```powershell
pnpm web
```

- Start CLI (auto-starts API if needed):

```powershell
pnpm cli
pnpm cli -- --help
pnpm cli -- audit sample.csv --program CSE
```

- Start mobile (Expo):

```powershell
pnpm dev:mobile
```

- Run all checks:

```powershell
pnpm test:all
```

### API-Only Run (manual)

If you only want FastAPI without web/CLI wrappers:

```powershell
cd packages\api
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

### MCP Server: Run + Smoke Test (Windows PowerShell)

```powershell
@'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
'@ | .\packages\api\.venv\Scripts\python.exe packages/api/mcp_server.py
```

Expected: one `initialize` response and one `tools/list` response containing tools like `audit_run`, `cgpa_breakdown`, `check_missing`.

Tool call smoke test:

```powershell
$csv = "Course_Code,Course_Name,Credits,Grade,Semester`nCSE115,Programming Language I,3,A,Spring 2024`nMAT125,Linear Algebra,3,B+,Spring 2024"
$req = @{ jsonrpc="2.0"; id=3; method="tools/call"; params=@{ name="audit_run"; arguments=@{ csv_text=$csv; program="CSE" } } } | ConvertTo-Json -Compress -Depth 10
$req | .\packages\api\.venv\Scripts\python.exe packages/api/mcp_server.py
```

Expected: output contains `"status": "success"` in tool response text.

### Local MCP Server

For safe project inspection and backend discovery tools, see `mcp_server/README.md`.

### Codex / AI Agent Bootstrap (copy-paste)

If you open this repo in Codex on a new machine, run this first so it has a real working baseline:

```powershell
git clone https://github.com/Pronaaf2k/nsu-transcript-audit.git
cd nsu-transcript-audit
Copy-Item .env.example .env
# fill .env values
pnpm setup:local
pnpm test:all
@'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
'@ | .\packages\api\.venv\Scripts\python.exe packages/api/mcp_server.py
```

Do not mix in ad-hoc package installs unless required; this repo is wired to `pnpm setup:local`.


## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/audit/extract` | Extract courses from PDF/image via OCR |
| POST | `/audit/run_csv` | Run full audit from CSV text |
| POST | `/audit/csv` | Upload CSV file directly |
| POST | `/audit/image` | Upload image/PDF and audit |
| GET | `/programs` | List canonical programs from `program.md` |
| GET | `/programs/{code}` | Get full requirements for one program |
| GET | `/history` | Get audit history |
| GET | `/history/{id}` | Get specific audit |

## CSV Format

```csv
Course_Code,Course_Name,Credits,Grade,Semester
CSE115,Programming Language I,3,A,Spring 2023
MAT116,Mathematics I,3,B+,Summer 2023
```

## Program Support

- CSE - Computer Science & Engineering
- BBA - Business Administration
- ETE - Electronic & Telecom Engineering
- ENG - English
- ECO - Economics
- ENV - Environmental Science & Management

## License

MIT License - See LICENSE file for details.
