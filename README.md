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
- Node.js 20+
- Python 3.11+
- Supabase account
- Gemini API key

### Local Development

1. **Clone the repo**
```bash
git clone https://github.com/Pronaaf2k/nsu-transcript-audit.git
cd nsu-transcript-audit
```

2. **Frontend**
```bash
cd packages/web
npm install
npm run dev
```

3. **Backend**
```bash
cd packages/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

4. **Environment Variables**

Frontend (`packages/web/.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Backend (`packages/api/.env`):
```
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/audit/extract` | Extract courses from PDF/image via OCR |
| POST | `/audit/run_csv` | Run full audit from CSV text |
| POST | `/audit/csv` | Upload CSV file directly |
| POST | `/audit/image` | Upload image/PDF and audit |
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
- EEE - Electrical & Electronic Engineering
- ECE - Electronics & Computer Engineering
- ENG - English
- ECO - Economics
- ENV - Environmental Science
- PHY - Physics

## License

MIT License - See LICENSE file for details.
