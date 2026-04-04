-- 002_audit_tables.sql
CREATE TABLE IF NOT EXISTS public.transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT,
  course TEXT NOT NULL,
  credits NUMERIC(5,2),
  grade TEXT,
  semester TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.audit_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id TEXT,
  program TEXT NOT NULL,
  audit_level INT NOT NULL,
  cgpa NUMERIC(4,2),
  eligible BOOLEAN,
  missing_courses JSONB,
  advisories JSONB,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
