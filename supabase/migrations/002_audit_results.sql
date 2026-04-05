-- audit_results table for NSU Transcript Audit
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.audit_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    scan_id UUID REFERENCES public.transcript_scans(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    program TEXT NOT NULL,
    audit_level INTEGER NOT NULL,
    cgpa NUMERIC(4,2),
    total_credits NUMERIC(5,2),
    graduation_status TEXT CHECK (graduation_status IN ('PASS', 'FAIL', 'PENDING')),
    missing_courses JSONB,
    advisories JSONB,
    result_json JSONB
);

ALTER TABLE public.audit_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own audits" ON public.audit_results
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users insert own audits" ON public.audit_results
    FOR INSERT WITH CHECK (auth.uid() = user_id);
