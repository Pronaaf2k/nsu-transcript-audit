-- ============================================================
-- 001_initial.sql  —  NSU Transcript Audit initial schema
-- Run via: supabase db push   OR paste into Supabase SQL editor
-- ============================================================

-- transcript_scans: one row per upload/audit invocation
CREATE TABLE IF NOT EXISTS public.transcript_scans (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- input metadata
  source_type  TEXT        NOT NULL CHECK (source_type IN ('image', 'pdf', 'csv')),
  storage_path TEXT,                         -- object path in Supabase Storage
  file_name    TEXT,                         -- original filename shown to user

  -- processing results (populated by Edge Function)
  raw_ocr      JSONB,                        -- raw response from Google Vision
  parsed_data  JSONB,                        -- normalised course list
  audit_result JSONB,                        -- L1 / L2 / L3 output
  program      TEXT,                         -- e.g. "CSE", "BBA"
  student_id   TEXT,                         -- extracted from transcript

  -- denormalised summary for quick list views
  total_credits     NUMERIC(5,2),
  cgpa              NUMERIC(4,2),
  graduation_status TEXT CHECK (graduation_status IN ('PASS', 'FAIL', 'PENDING', 'ERROR'))
);

-- ── Indexes ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_scans_user_id     ON public.transcript_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_created_at  ON public.transcript_scans(created_at DESC);

-- ── Row-Level Security ───────────────────────────────────────
ALTER TABLE public.transcript_scans ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own scans
CREATE POLICY "Users own their scans" ON public.transcript_scans
  FOR ALL
  USING  (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ── Storage bucket ───────────────────────────────────────────
-- Create via Supabase Dashboard or with supabase-cli:
--   supabase storage create-bucket transcripts --public false
-- Corresponding RLS on storage objects:
--   Users can upload to their own folder: transcripts/{user_id}/*
INSERT INTO storage.buckets (id, name, public)
VALUES ('transcripts', 'transcripts', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "User upload own folder" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'transcripts' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "User read own folder"   ON storage.objects
  FOR SELECT TO authenticated
  USING  (bucket_id = 'transcripts' AND (storage.foldername(name))[1] = auth.uid()::text);
