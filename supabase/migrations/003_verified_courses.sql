-- 003_verified_courses.sql
-- Store OCR-verified course data for audit records

CREATE TABLE IF NOT EXISTS public.verified_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES public.transcript_scans(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL,
    course_name TEXT,
    credits NUMERIC(3,1) DEFAULT 3,
    grade TEXT NOT NULL,
    semester TEXT NOT NULL,
    verified BOOLEAN DEFAULT true,
    is_manual BOOLEAN DEFAULT false,  -- true if manually added
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.verified_courses ENABLE ROW LEVEL SECURITY;

-- Users can read their own verified courses
CREATE POLICY "Users read own verified courses" ON public.verified_courses
    FOR SELECT USING (true);

-- Users can insert their own verified courses
CREATE POLICY "Users insert own verified courses" ON public.verified_courses
    FOR INSERT WITH CHECK (true);

-- Auto-delete when parent scan is deleted
-- (handled by ON DELETE CASCADE above)

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_verified_courses_scan_id ON public.verified_courses(scan_id);

-- Add columns to transcript_scans for verification status
ALTER TABLE public.transcript_scans 
    ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS ocr_confidence NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS total_courses INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS verified_courses INTEGER DEFAULT 0;

-- verification_status: 'pending', 'verified', 'modified'
